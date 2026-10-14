"""Usuarios, sesiones firmadas y control de acceso (prueba gratis / suscripción)."""
import base64
import hashlib
import hmac
import json
import math
import os
import re
import threading
import time

from . import config, db, plans

ITER = 200_000
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DAY = 86400


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# ---------- contraseñas ----------
def hash_pw(pw: str) -> str:
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, ITER)
    return f"pbkdf2${ITER}${salt.hex()}${h.hex()}"


def verify_pw(pw: str, stored: str) -> bool:
    try:
        _, it, salt, h = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(it))
        return hmac.compare_digest(calc.hex(), h)
    except Exception:
        return False


# ---------- token de sesión ----------
def make_token(uid: int, ttl: int = 30 * DAY) -> str:
    payload = _b64(json.dumps({"u": uid, "e": int(time.time() + ttl)}).encode())
    sig = _b64(hmac.new(config.SECRET, payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def read_token(tok: str):
    try:
        payload, sig = tok.split(".")
        good = _b64(hmac.new(config.SECRET, payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, good):
            return None
        d = json.loads(_unb64(payload))
        if d["e"] < time.time():
            return None
        return int(d["u"])
    except Exception:
        return None


# ---------- límite de intentos ----------
_fails = {}
_fl = threading.Lock()


def too_many_attempts(key: str, limit=6, window=600) -> bool:
    now = time.time()
    with _fl:
        _fails[key] = [t for t in _fails.get(key, []) if now - t < window]
        return len(_fails[key]) >= limit


def register_fail(key: str):
    with _fl:
        _fails.setdefault(key, []).append(time.time())


def clear_fails(key: str):
    with _fl:
        _fails.pop(key, None)


# ---------- usuarios ----------
def get_user(uid: int):
    return db.q1("SELECT * FROM users WHERE id=?", (uid,))


def get_user_by_email(email: str):
    return db.q1("SELECT * FROM users WHERE email=?", (email.strip().lower(),))


def create_user(email: str, password: str, name: str = "", role: str | None = None, trial_days: int | None = None, plan: str = "avanzado", ref: str | None = None):
    email = (email or "").strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 200:
        raise ValueError("Correo no válido")
    if len(password or "") < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    if get_user_by_email(email):
        raise ValueError("Ese correo ya está registrado")
    if not plans.valid(plan):
        raise ValueError("Plan no válido")
    if role is None:
        role = "admin" if config.ADMIN_EMAIL and email == config.ADMIN_EMAIL else "user"
    days = config.TRIAL_DAYS if trial_days is None else trial_days
    now = int(time.time())
    uid = db.x(
        "INSERT INTO users(email,name,pw_hash,role,created_at,trial_ends,plan) VALUES(?,?,?,?,?,?,?)",
        (email, (name or "").strip()[:80], hash_pw(password), role, now, now + days * DAY, plan),
    )
    try:
        from . import referrals
        referrals.ensure_code(uid)
        if ref:
            referrals.register(uid, ref)
    except Exception:  # los referidos nunca deben impedir un registro
        pass
    return get_user(uid)


def access_info(u) -> dict:
    """Decide si el usuario puede entrar a la app."""
    now = int(time.time())
    base = {"access": False, "reason": "expired", "trial_days_left": 0, "sub_ends": u["sub_ends"], "sub_status": u["sub_status"]}
    if u["role"] == "admin":
        return {**base, "access": True, "reason": "admin"}
    if u["sub_status"] == "active":
        if not u["sub_ends"] or u["sub_ends"] + config.PAST_DUE_GRACE_DAYS * DAY > now:
            return {**base, "access": True, "reason": "active"}
    if u["trial_ends"] and u["trial_ends"] > now:
        return {**base, "access": True, "reason": "trial", "trial_days_left": math.ceil((u["trial_ends"] - now) / DAY)}
    if "reward_until" in u.keys() and (u["reward_until"] or 0) > now:  # meses gratis ganados por referidos
        return {**base, "access": True, "reason": "reward", "reward_days_left": math.ceil((u["reward_until"] - now) / DAY)}
    if u["sub_status"] == "canceled":
        base["reason"] = "canceled"
    elif u["sub_status"] == "past_due":
        base["reason"] = "past_due"
    return base


def public_user(u) -> dict:
    ep = plans.effective_plan(u)
    info = access_info(u)
    return {
        "id": u["id"], "email": u["email"], "name": u["name"], "role": u["role"],
        "created_at": u["created_at"], "trial_ends": u["trial_ends"], **info,
        "plan": ep, "plan_name": plans.PLANS[ep]["name"], "plan_set": u["plan"],
        "modules": plans.PLANS[ep]["modules"] if info["access"] else ["cuenta", "planes"],
        "custom_limit": plans.CUSTOM_LIMIT[ep],
        "reward_until": u["reward_until"] if "reward_until" in u.keys() else None,
    }


def admin_update(uid: int, action: str, value=None):
    u = get_user(uid)
    if not u:
        raise ValueError("Usuario no existe")
    now = int(time.time())
    if action == "grant_days":
        days = int(value)
        if not (-3650 <= days <= 3650):
            raise ValueError("Días fuera de rango")
        base = max(u["sub_ends"] or 0, now) if u["sub_status"] == "active" else now
        db.x("UPDATE users SET sub_status='active', sub_ends=? WHERE id=?", (base + days * DAY, uid))
    elif action == "extend_trial":
        days = int(value)
        base = max(u["trial_ends"] or 0, now)
        db.x("UPDATE users SET trial_ends=? WHERE id=?", (base + days * DAY, uid))
    elif action == "set_status":
        if value not in ("none", "active", "past_due", "canceled"):
            raise ValueError("Estado no válido")
        db.x("UPDATE users SET sub_status=? WHERE id=?", (value, uid))
    elif action == "set_role":
        if value not in ("user", "admin"):
            raise ValueError("Rol no válido")
        db.x("UPDATE users SET role=? WHERE id=?", (value, uid))
    elif action == "set_plan":
        if not plans.valid(value):
            raise ValueError("Plan no válido")
        db.x("UPDATE users SET plan=? WHERE id=?", (value, uid))
    elif action == "revoke":
        db.x("UPDATE users SET sub_status='canceled', sub_ends=?, trial_ends=? WHERE id=?", (now, now, uid))
    else:
        raise ValueError("Acción desconocida")
    return get_user(uid)
