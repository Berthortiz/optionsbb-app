"""Planes de suscripción y qué incluye cada uno (se aplica en el servidor, no solo en pantalla)."""
from . import config, db, strategies

ORDER = ["basico", "intermedio", "avanzado"]
RANK = {p: i + 1 for i, p in enumerate(ORDER)}

PLANS = {
    "basico": {
        "name": "Básico",
        "tagline": "Para empezar con orden",
        "modules": ["inicio", "empezar", "comando", "listas", "analisis", "covercall", "escenarios", "etf", "dividendos", "k401", "videos", "referidos", "manual", "cuenta", "planes"],
        "features": ["Acceso a las acciones del Centro de Comando y tu lista de seguimiento", "2 estrategias: 1 alcista y 1 bajista",
                     "Análisis de acciones por temporalidad", "Módulo Cover Call (calculadora y simulador)", "Listas Optionsbb (poco, moderado y alto riesgo) y tu propio ETF", "Ejemplos «¿Qué hubiera pasado si…?»", "Módulo 401(k) / retiro",
                     "Biblioteca de videos (nivel básico)"],
    },
    "intermedio": {
        "name": "Intermedio",
        "tagline": "Más estrategias, sectores y ranking",
        "modules": ["inicio", "empezar", "comando", "listas", "analisis", "covercall", "opciones", "escenarios", "etf", "dividendos", "k401", "videos", "sectores", "ranking", "desempeno", "referidos", "manual", "cuenta", "planes"],
        "features": ["Todo lo del plan Básico", "5 estrategias alcistas y 5 bajistas adicionales (6 + 6 en total)",
                     "Sectores", "Desempeño (reportes de backtesting)",
                     "Ranking de estrategias más efectivas", "Cover Call y 401(k)", "Videos hasta nivel intermedio"],
    },
    "avanzado": {
        "name": "Avanzado",
        "tagline": "Todo, más tus propias estrategias",
        "modules": ["inicio", "empezar", "comando", "listas", "analisis", "covercall", "escenarios", "etf", "dividendos", "opciones", "earnings", "gex", "apalancados", "k401", "videos", "flujo", "sectores", "ranking", "desempeno", "senales", "referidos", "manual", "cuenta", "planes"],
        "features": ["Todo lo de Básico e Intermedio", "Flujo OI (volumen → open interest)", "Cover Call + acciones apalancadas (NVDL, AMDL…)", "Todas las estrategias (10 alcistas + 10 bajistas)",
                     "2 estrategias personalizadas", "Alarmas y señales de estrategias de mentores (hispanos y americanos)",
                     "Toda la biblioteca de videos"],
    },
}
CUSTOM_LIMIT = {"basico": 0, "intermedio": 0, "avanzado": 2}
STRATEGY_TIER = {"basico": 1, "intermedio": 2, "avanzado": 3}
MODULE_MIN = {"inicio": "basico", "empezar": "basico", "analisis": "basico", "k401": "basico", "manual": "basico", "listas": "basico", "ranking": "intermedio", "comando": "basico", "covercall": "basico", "videos": "basico", "cuenta": "basico", "planes": "basico",
              "escenarios": "basico", "referidos": "basico", "dividendos": "basico", "opciones": "intermedio", "earnings": "avanzado", "gex": "avanzado", "etf": "basico", "apalancados": "avanzado", "flujo": "avanzado", "sectores": "intermedio", "desempeno": "intermedio", "senales": "avanzado"}


def valid(plan) -> bool:
    return plan in PLANS


def effective_plan(u) -> str:
    if u["role"] == "admin":
        return "avanzado"
    import time
    if "reward_until" in u.keys() and (u["reward_until"] or 0) > time.time():
        return "avanzado"  # meses gratis por referidos = plan Avanzado
    p = u["plan"] if "plan" in u.keys() else "avanzado"
    return p if p in PLANS else "basico"


def has_module(plan: str, module: str) -> bool:
    return module in PLANS[plan]["modules"]


def allowed_strategy_ids(plan: str) -> list:
    t = STRATEGY_TIER[plan]
    return [s["id"] for s in strategies.STRATEGIES if s["tier"] <= t]


def at_least(plan: str, need: str) -> bool:
    return RANK[plan] >= RANK[need]


def price_label(plan: str) -> str:
    return db.kv_get("plan_price_" + plan, "") or ""


def catalog(current: str | None = None) -> list:
    out = []
    for pid in ORDER:
        p = PLANS[pid]
        t = STRATEGY_TIER[pid]
        out.append({
            "id": pid, "name": p["name"], "tagline": p["tagline"], "features": p["features"], "modules": p["modules"],
            "bull": sum(1 for s in strategies.STRATEGIES if s["side"] == "BULL" and s["tier"] <= t),
            "bear": sum(1 for s in strategies.STRATEGIES if s["side"] == "BEAR" and s["tier"] <= t),
            "custom": CUSTOM_LIMIT[pid], "price_label": price_label(pid), "current": pid == current,
            "checkout": bool(config.STRIPE_PRICES.get(pid)),
        })
    return out
