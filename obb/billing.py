"""Cobro de la suscripción mensual con Stripe (opcional). Solo librería estándar."""
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from . import config, db, plans

API = "https://api.stripe.com/v1"


class BillingError(Exception):
    pass


def configured() -> bool:
    return bool(config.STRIPE_SECRET and any(config.STRIPE_PRICES.values()))


def plan_for_price(price_id):
    for pid, pr in config.STRIPE_PRICES.items():
        if pr and pr == price_id:
            return pid
    return None


def _plan_of_sub(obj):
    try:
        return plan_for_price(obj["items"]["data"][0]["price"]["id"])
    except Exception:
        return None


def _post(path: str, fields: dict) -> dict:
    if not config.STRIPE_SECRET:
        raise BillingError("Stripe no está configurado")
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(API + path, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {config.STRIPE_SECRET}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise BillingError(f"Stripe respondió {e.code}: {e.read()[:200].decode(errors='replace')}")
    except Exception as e:  # red caída, etc.
        raise BillingError(f"No se pudo contactar a Stripe: {e}")


def _get(path: str) -> dict:
    if not config.STRIPE_SECRET:
        raise BillingError("Stripe no está configurado")
    req = urllib.request.Request(API + path, method="GET")
    req.add_header("Authorization", f"Bearer {config.STRIPE_SECRET}")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise BillingError(f"Stripe respondió {e.code}: {e.read()[:200].decode(errors='replace')}")
    except Exception as e:
        raise BillingError(f"No se pudo contactar a Stripe: {e}")


def attach_coupon(customer: str, pct: int, months: int) -> str:
    """Crea un cupón (pct % de descuento durante `months` cobros) y lo pone en la suscripción activa del cliente.
    SIN PROBAR contra Stripe real: se ejecuta en modo «mejor esfuerzo» y cualquier error queda anotado para aplicarlo a mano."""
    c = {"percent_off": str(int(pct)), "name": f"Referidos Optionsbb {pct}%"}
    if months == 1:
        c["duration"] = "once"
    else:
        c.update({"duration": "repeating", "duration_in_months": str(int(months))})
    coupon = _post("/coupons", c)
    subs = _get("/subscriptions?" + urllib.parse.urlencode({"customer": customer, "status": "active", "limit": "1"}))
    data = subs.get("data") or []
    if not data:
        raise BillingError("El cliente no tiene una suscripción activa en Stripe")
    _post(f"/subscriptions/{data[0]['id']}", {"discounts[0][coupon]": coupon["id"]})
    return f"Cupón {coupon['id']} aplicado en Stripe"


def checkout_url(user, plan: str | None = None) -> str:
    if not configured():
        raise BillingError("El cobro automático aún no está configurado. Contacta al administrador.")
    plan = plan or plans.effective_plan(user)
    if not plans.valid(plan):
        raise BillingError("Plan no válido")
    price = config.STRIPE_PRICES.get(plan)
    if not price:
        raise BillingError(f"El plan {plans.PLANS[plan]['name']} aún no tiene precio configurado en Stripe.")
    f = {
        "mode": "subscription",
        "metadata[plan]": plan,
        "subscription_data[metadata][plan]": plan,
        "line_items[0][price]": price,
        "line_items[0][quantity]": "1",
        "success_url": config.PUBLIC_URL + "/?pago=ok",
        "cancel_url": config.PUBLIC_URL + "/?pago=cancelado",
        "client_reference_id": str(user["id"]),
        "allow_promotion_codes": "true",
    }
    if user["stripe_customer"]:
        f["customer"] = user["stripe_customer"]
    else:
        f["customer_email"] = user["email"]
    return _post("/checkout/sessions", f)["url"]


def portal_url(user) -> str:
    if not user["stripe_customer"]:
        raise BillingError("Aún no tienes una suscripción en Stripe")
    return _post("/billing_portal/sessions", {"customer": user["stripe_customer"], "return_url": config.PUBLIC_URL + "/"})["url"]


# ---------- webhook ----------
def verify_signature(payload: bytes, header: str, secret: str, tolerance: int = 300, now: float | None = None) -> bool:
    """Firma de Stripe: header 't=...,v1=...' ; HMAC-SHA256 de '{t}.{payload}'."""
    try:
        parts = [p.split("=", 1) for p in header.split(",") if "=" in p]
        t = next(v for k, v in parts if k == "t")
        sigs = [v for k, v in parts if k == "v1"]
        if abs((now or time.time()) - int(t)) > tolerance:
            return False
        expected = hmac.new(secret.encode(), t.encode() + b"." + payload, hashlib.sha256).hexdigest()
        return any(hmac.compare_digest(expected, s) for s in sigs)
    except Exception:
        return False


def _period_end(obj: dict):
    if obj.get("current_period_end"):
        return int(obj["current_period_end"])
    try:
        return int(obj["items"]["data"][0]["current_period_end"])
    except Exception:
        return None


def _user_for(customer, ref=None):
    if ref and str(ref).isdigit():
        r = db.q1("SELECT * FROM users WHERE id=?", (int(ref),))
        if r:
            return r
    if customer:
        return db.q1("SELECT * FROM users WHERE stripe_customer=?", (customer,))
    return None


def handle_event(ev: dict) -> str:
    typ = ev.get("type", "")
    obj = ev.get("data", {}).get("object", {})
    if typ == "checkout.session.completed":
        u = _user_for(obj.get("customer"), obj.get("client_reference_id"))
        if not u:
            return "usuario no encontrado"
        db.x(
            "UPDATE users SET stripe_customer=?, sub_status='active', sub_ends=? WHERE id=?",
            (obj.get("customer"), int(time.time()) + 35 * 86400, u["id"]),
        )
        pl = (obj.get("metadata") or {}).get("plan")
        if plans.valid(pl):
            db.x("UPDATE users SET plan=? WHERE id=?", (pl, u["id"]))
        try:
            from . import referrals
            referrals.qualify(u["id"])  # el referido pagó: cuenta para quien lo invitó
            referrals.activate_next_discount(u["id"])
        except Exception:
            import logging
            logging.getLogger("obb.billing").exception("Referidos: no se pudo procesar el pago")
        return "activado"
    if typ == "invoice.paid":
        u = _user_for(obj.get("customer"))
        if not u:
            return "usuario no encontrado"
        end = None
        try:
            end = int(obj["lines"]["data"][0]["period"]["end"])
        except Exception:
            pass
        db.x("UPDATE users SET sub_status='active', sub_ends=? WHERE id=?", (end or int(time.time()) + 35 * 86400, u["id"]))
        try:
            from . import referrals
            referrals.qualify(u["id"])  # por si el primer pago llegó primero como invoice.paid
            referrals.on_invoice_paid(u["id"])
        except Exception:
            import logging
            logging.getLogger("obb.billing").exception("Referidos: no se pudo procesar la renovación")
        return "renovado"
    if typ == "invoice.payment_failed":
        u = _user_for(obj.get("customer"))
        if u:
            db.x("UPDATE users SET sub_status='past_due' WHERE id=?", (u["id"],))
        return "pago fallido"
    if typ in ("customer.subscription.updated", "customer.subscription.deleted"):
        u = _user_for(obj.get("customer"))
        if not u:
            return "usuario no encontrado"
        st = obj.get("status")
        if typ.endswith("deleted") or st in ("canceled", "unpaid", "incomplete_expired"):
            db.x("UPDATE users SET sub_status='canceled', sub_ends=? WHERE id=?", (int(time.time()), u["id"]))
            return "cancelado"
        if st in ("active", "trialing"):
            pl = _plan_of_sub(obj) or (obj.get("metadata") or {}).get("plan")
            if plans.valid(pl):
                db.x("UPDATE users SET plan=? WHERE id=?", (pl, u["id"]))
            db.x("UPDATE users SET sub_status='active', sub_ends=COALESCE(?, sub_ends) WHERE id=?", (_period_end(obj), u["id"]))
            return "activo"
        if st == "past_due":
            db.x("UPDATE users SET sub_status='past_due' WHERE id=?", (u["id"],))
            return "mora"
    return "ignorado"
