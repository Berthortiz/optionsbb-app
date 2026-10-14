"""Contenido editable de las pantallas de bienvenida: tasas del banco y guía «¿Por dónde empiezo?»."""
import json

from . import db

DEFAULTS = {
    "bank_pays": 1.43,       # % anual que paga el banco por tu dinero
    "bank_charges": 26.0,    # % anual que cobra el banco (tarjeta / préstamo)
    "cc_low": 0.5,           # % mensual orientativo de prima de cover call (rango bajo)
    "cc_high": 2.0,          # % mensual orientativo (rango alto)
    "examples": ["F", "SOFI", "KO", "AAPL"],   # acciones para mostrar cuánto capital pide 1 contrato de cover call
}


def get() -> dict:
    d = dict(DEFAULTS)
    try:
        d.update(json.loads(db.kv_get("guide", "") or "{}"))
    except ValueError:
        pass
    return d


def _num(v, lo, hi, name):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{name}: número no válido")
    if not lo <= x <= hi:
        raise ValueError(f"{name}: debe estar entre {lo} y {hi}")
    return round(x, 2)


def set_(d) -> dict:
    if not isinstance(d, dict):
        raise ValueError("Datos no válidos")
    cur = get()
    for k, lo, hi in (("bank_pays", 0, 100), ("bank_charges", 0, 100), ("cc_low", 0, 50), ("cc_high", 0, 50)):
        if k in d:
            cur[k] = _num(d[k], lo, hi, k)
    if cur["cc_low"] > cur["cc_high"]:
        raise ValueError("cc_low no puede superar a cc_high")
    if "examples" in d:
        ex = [str(s).upper().strip() for s in (d["examples"] or []) if str(s).strip()]
        if not ex or len(ex) > 8 or not all(s.isalpha() and len(s) <= 6 for s in ex):
            raise ValueError("examples: 1 a 8 símbolos")
        cur["examples"] = ex
    db.kv_set("guide", json.dumps(cur))
    return cur
