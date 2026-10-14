"""Sistema de referidos.

- Cada usuario tiene un código y un enlace (https://tu-dominio/?ref=CODIGO).
- Un referido cuenta cuando PAGA su primera suscripción (no cuando solo se registra o está en prueba).
- Premios para quien refiere (reglas editables por el administrador):
    · por cada referido que se suscribe  → 20 % de descuento en su siguiente mes (un descuento por mes, se acumulan en cola)
    · al llegar a 10 referidos          → 6 meses gratis del plan Avanzado
    · al llegar a 20 referidos          → 12 meses gratis del plan Avanzado (se suma al premio anterior)
- Los meses gratis dan acceso Avanzado dentro de la app (users.reward_until). Si el usuario paga con Stripe, además se
  intenta aplicar un cupón en Stripe (sin esa parte el cobro seguiría); lo que no se pueda aplicar queda en la lista del
  administrador como «pendiente de aplicar a mano».
"""
import json
import logging
import secrets
import time

from . import billing, config, db

log = logging.getLogger("obb.referrals")
DAY = 86400
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0/O/1/I
DEFAULT_RULES = {"disc_pct": 20, "milestones": [{"n": 10, "months": 6}, {"n": 20, "months": 12}]}


# ---------------------------------------------------------------- reglas
def rules() -> dict:
    try:
        r = json.loads(db.kv_get("ref_rules", "") or "null")
    except ValueError:
        r = None
    return r if isinstance(r, dict) and "milestones" in r else json.loads(json.dumps(DEFAULT_RULES))


def set_rules(d: dict) -> dict:
    try:
        pct = int(d.get("disc_pct"))
        ms = [{"n": int(m["n"]), "months": int(m["months"])} for m in d.get("milestones", [])]
    except (TypeError, ValueError, KeyError):
        raise ValueError("Reglas no válidas")
    if not 0 <= pct <= 100:
        raise ValueError("El descuento debe estar entre 0 y 100")
    if not ms or len(ms) > 6 or any(not (1 <= m["n"] <= 1000 and 1 <= m["months"] <= 60) for m in ms):
        raise ValueError("Cada meta necesita referidos (1–1000) y meses (1–60)")
    ms.sort(key=lambda m: m["n"])
    if len({m["n"] for m in ms}) != len(ms):
        raise ValueError("No repitas el número de referidos")
    out = {"disc_pct": pct, "milestones": ms}
    db.kv_set("ref_rules", json.dumps(out))
    return out


# ---------------------------------------------------------------- códigos
def ensure_code(uid: int) -> str:
    u = db.q1("SELECT ref_code FROM users WHERE id=?", (uid,))
    if u and u["ref_code"]:
        return u["ref_code"]
    for _ in range(20):
        code = "".join(secrets.choice(ALPHABET) for _ in range(7))
        if not db.q1("SELECT 1 FROM users WHERE ref_code=?", (code,)):
            db.x("UPDATE users SET ref_code=? WHERE id=?", (code, uid))
            return code
    raise RuntimeError("No se pudo generar el código")


def by_code(code):
    code = (code or "").strip().upper()
    if not (4 <= len(code) <= 12):
        return None
    return db.q1("SELECT * FROM users WHERE ref_code=?", (code,))


def register(new_uid: int, code) -> bool:
    """Liga al usuario nuevo con quien lo invitó. Devuelve False si el código no sirve (no bloquea el registro)."""
    ref = by_code(code)
    me = db.q1("SELECT * FROM users WHERE id=?", (new_uid,))
    if not ref or not me or ref["id"] == new_uid or me["referred_by"]:
        return False
    db.x("UPDATE users SET referred_by=? WHERE id=?", (ref["id"], new_uid))
    db.x("INSERT OR IGNORE INTO referrals(referrer_id,referred_id,status,created_at) VALUES(?,?,'registered',?)", (ref["id"], new_uid, int(time.time())))
    return True


def claim(uid: int, code) -> None:
    me = db.q1("SELECT * FROM users WHERE id=?", (uid,))
    if me["referred_by"]:
        raise ValueError("Ya tienes un código de referido registrado")
    if me["sub_status"] == "active":
        raise ValueError("Solo puedes agregar un código antes de suscribirte")
    ref = by_code(code)
    if not ref or ref["id"] == uid:
        raise ValueError("Ese código no es válido")
    register(uid, code)


# ---------------------------------------------------------------- premios
def _grant(uid, kind, **kw):
    return db.x("INSERT INTO referral_rewards(user_id,kind,pct,months,milestone,status,created_at,note) VALUES(?,?,?,?,?,?,?,?)",
                (uid, kind, kw.get("pct", 0), kw.get("months", 0), kw.get("milestone", 0), kw.get("status", "pending"), int(time.time()), kw.get("note", "")))


def _stripe_coupon(user, pct, months):
    """Mejor esfuerzo: cupón en la suscripción de Stripe. Devuelve (ok, nota)."""
    if not user["stripe_customer"] or not config.STRIPE_SECRET:
        return False, "Sin Stripe: aplicar a mano"
    try:
        return True, billing.attach_coupon(user["stripe_customer"], pct, months)
    except Exception as e:  # nunca debe romper el flujo de pago
        log.warning("Cupón de Stripe no aplicado: %s", e)
        return False, f"Stripe no aplicó el cupón ({e}): aplicar a mano"


def activate_next_discount(uid: int):
    """Mantiene a lo sumo UN descuento activo (el del próximo cobro); el resto espera en cola."""
    if db.q1("SELECT 1 FROM referral_rewards WHERE user_id=? AND kind='disc' AND status='active'", (uid,)):
        return
    nxt = db.q1("SELECT * FROM referral_rewards WHERE user_id=? AND kind='disc' AND status='pending' ORDER BY id LIMIT 1", (uid,))
    if not nxt:
        return
    user = db.q1("SELECT * FROM users WHERE id=?", (uid,))
    if user["sub_status"] != "active":
        return  # se activará cuando el usuario esté suscrito
    ok, note = _stripe_coupon(user, nxt["pct"], 1)
    db.x("UPDATE referral_rewards SET status='active', applied_at=?, note=?, manual=? WHERE id=?", (int(time.time()), str(note)[:200], 0 if ok else 1, nxt["id"]))


def qualify(referred_uid: int) -> dict | None:
    """El referido pagó: cuenta para quien lo invitó. Es idempotente."""
    r = db.q1("SELECT * FROM referrals WHERE referred_id=? AND status='registered'", (referred_uid,))
    if not r:
        return None
    now = int(time.time())
    db.x("UPDATE referrals SET status='qualified', qualified_at=? WHERE id=?", (now, r["id"]))
    rid, rules_ = r["referrer_id"], rules()
    n = db.q1("SELECT COUNT(*) c FROM referrals WHERE referrer_id=? AND status='qualified'", (rid,))["c"]
    if rules_["disc_pct"] > 0:
        _grant(rid, "disc", pct=rules_["disc_pct"], note="Referido que se suscribió")
    granted = []
    for m in rules_["milestones"]:
        if n >= m["n"] and not db.q1("SELECT 1 FROM referral_rewards WHERE user_id=? AND kind='free' AND milestone=?", (rid, m["n"])):
            until = _extend_free(rid, m["months"])
            user = db.q1("SELECT * FROM users WHERE id=?", (rid,))
            ok, note = _stripe_coupon(user, 100, m["months"]) if user["sub_status"] == "active" else (True, "Meses gratis dentro de la app")
            _grant(rid, "free", months=m["months"], milestone=m["n"], status="applied", note=str(note)[:200])
            if not ok:
                db.x("UPDATE referral_rewards SET manual=1 WHERE user_id=? AND kind='free' AND milestone=?", (rid, m["n"]))
            granted.append({"n": m["n"], "months": m["months"], "until": until})
    activate_next_discount(rid)
    return {"referrer": rid, "qualified": n, "milestones": granted}


def _extend_free(uid: int, months: int) -> int:
    u = db.q1("SELECT reward_until FROM users WHERE id=?", (uid,))
    base = max(int(time.time()), u["reward_until"] or 0)
    until = base + months * 30 * DAY
    db.x("UPDATE users SET reward_until=? WHERE id=?", (until, uid))
    return until


def on_invoice_paid(uid: int):
    """Un cobro se completó: el descuento activo ya se usó; activa el siguiente de la cola."""
    db.x("UPDATE referral_rewards SET status='used' WHERE user_id=? AND kind='disc' AND status='active'", (uid,))
    activate_next_discount(uid)


# ---------------------------------------------------------------- vistas
def _mask(email: str) -> str:
    name, _, dom = email.partition("@")
    return (name[:2] + "***") + "@" + (dom[:1] + "***" + dom[dom.rfind("."):] if "." in dom else "***")


def overview(uid: int) -> dict:
    code = ensure_code(uid)
    rl = rules()
    rows = db.q("SELECT r.status, r.created_at, r.qualified_at, u.email FROM referrals r JOIN users u ON u.id=r.referred_id WHERE r.referrer_id=? ORDER BY r.id DESC", (uid,))
    q = sum(1 for r in rows if r["status"] == "qualified")
    rewards = db.q("SELECT * FROM referral_rewards WHERE user_id=? ORDER BY id DESC LIMIT 100", (uid,))
    me = db.q1("SELECT reward_until, referred_by FROM users WHERE id=?", (uid,))
    nxt = next((m for m in rl["milestones"] if m["n"] > q), None)
    return {
        "code": code, "link": f"{config.PUBLIC_URL}/?ref={code}", "rules": rl,
        "registered": len(rows), "qualified": q, "next": nxt, "missing": (nxt["n"] - q) if nxt else 0,
        "referred": [{"who": _mask(r["email"]), "status": r["status"], "date": r["created_at"], "qualified_at": r["qualified_at"]} for r in rows],
        "rewards": [{"id": w["id"], "kind": w["kind"], "pct": w["pct"], "months": w["months"], "milestone": w["milestone"], "status": w["status"], "date": w["created_at"], "note": w["note"]} for w in rewards],
        "discounts_waiting": sum(1 for w in rewards if w["kind"] == "disc" and w["status"] in ("pending", "active")),
        "reward_until": me["reward_until"], "has_referrer": bool(me["referred_by"]),
    }


def admin_overview() -> dict:
    top = db.q("""SELECT u.id, u.email, SUM(r.status='qualified') q, COUNT(*) total FROM referrals r JOIN users u ON u.id=r.referrer_id GROUP BY u.id ORDER BY q DESC, total DESC LIMIT 50""")
    manual = db.q("""SELECT w.id, w.kind, w.pct, w.months, w.note, w.created_at, u.email FROM referral_rewards w JOIN users u ON u.id=w.user_id WHERE w.manual=1 AND w.status IN ('active','applied') AND w.done=0 ORDER BY w.id DESC LIMIT 100""")
    pend = db.q("""SELECT r.referred_id, ue.email referred, ur.email referrer, r.created_at FROM referrals r JOIN users ue ON ue.id=r.referred_id JOIN users ur ON ur.id=r.referrer_id WHERE r.status='registered' ORDER BY r.id DESC LIMIT 100""")
    return {"rules": rules(), "top": [dict(r) for r in top], "manual": [dict(r) for r in manual], "pending": [dict(r) for r in pend]}


def mark_done(reward_id: int):
    db.x("UPDATE referral_rewards SET done=1 WHERE id=?", (reward_id,))
