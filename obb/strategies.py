"""Detectores de patrones de velas (5 min) para las listas alcista/bajista.

NOTA: son definiciones genéricas del patrón (ver README). Si tu thinkScript (p. ej. OBB_VVV3, OBB_VRV)
usa reglas distintas, ajusta aquí cada función: cada una recibe la lista de velas `c` y el índice `i`.
"""
from datetime import datetime

from . import clock


def _red(x):
    return x["c"] < x["o"]


def _green(x):
    return x["c"] > x["o"]


def sma(c, n, i):
    if i + 1 < n:
        return None
    return sum(x["c"] for x in c[i + 1 - n:i + 1]) / n


# ---------------- alcistas ----------------
def vela_verde(c, i):
    """Patrón de 5 velas: 3 rojas seguidas, 2 verdes; la vela 5 cierra sobre el cierre de la 4 (entrada)."""
    if i < 4:
        return False
    a, b, d, e, f = c[i - 4:i + 1]
    return _red(a) and _red(b) and _red(d) and _green(e) and _green(f) and f["c"] > e["c"]


def _wicks(x):
    top, bot = max(x["o"], x["c"]), min(x["o"], x["c"])
    return x["h"] - x["l"], x["h"] - top, bot - x["l"], top - bot  # rango, mecha sup, mecha inf, cuerpo


def martillo(c, i):
    if i < 3:
        return False
    rng, up, lo, body = _wicks(c[i])
    if rng <= 0:
        return False
    return lo >= 0.6 * rng and up <= 0.15 * rng and body <= 0.35 * rng and c[i - 1]["c"] < c[i - 3]["c"]


def cruce_alcista(c, i):
    if i < 21:
        return False
    a, b, d, e = sma(c, 9, i), sma(c, 21, i), sma(c, 9, i - 1), sma(c, 21, i - 1)
    return a > b and d <= e


def ruptura_resistencia(c, i):
    if i < 20:
        return False
    return c[i]["c"] > max(x["h"] for x in c[i - 20:i])


# ---------------- bajistas ----------------
def _day(x):
    return datetime.fromtimestamp(x["t"], clock.ET).date()


def vela_roja_apertura(c, i):
    """Primera vela de la sesión: roja, cuerpo >= 50 % del rango y cierra bajo el cierre anterior."""
    if i < 1:
        return False
    x = c[i]
    if _day(c[i - 1]) == _day(x):  # no es la primera vela del día
        return False
    rng, _, _, body = _wicks(x)
    return _red(x) and rng > 0 and body >= 0.5 * rng and x["c"] < c[i - 1]["c"]


def estrella_fugaz(c, i):
    if i < 3:
        return False
    rng, up, lo, body = _wicks(c[i])
    if rng <= 0:
        return False
    return up >= 0.6 * rng and lo <= 0.15 * rng and body <= 0.35 * rng and c[i - 1]["c"] > c[i - 3]["c"]


def cruce_bajista(c, i):
    if i < 21:
        return False
    a, b, d, e = sma(c, 9, i), sma(c, 21, i), sma(c, 9, i - 1), sma(c, 21, i - 1)
    return a < b and d >= e


def ruptura_soporte(c, i):
    if i < 20:
        return False
    return c[i]["c"] < min(x["l"] for x in c[i - 20:i])


# ---------------- ampliación (planes Intermedio y Avanzado) ----------------
def _body_pct(x):
    rng, _, _, body = _wicks(x)
    return body / rng if rng > 0 else 0.0


def _avg_vol(c, i, n=20):
    seg = [x.get("v") or 0 for x in c[max(0, i - n):i]]
    return sum(seg) / len(seg) if seg else 0


def envolvente_alcista(c, i):
    if i < 1:
        return False
    p, x = c[i - 1], c[i]
    return _red(p) and _green(x) and x["o"] <= p["c"] and x["c"] >= p["o"] and abs(x["c"] - x["o"]) > abs(p["o"] - p["c"])


def envolvente_bajista(c, i):
    if i < 1:
        return False
    p, x = c[i - 1], c[i]
    return _green(p) and _red(x) and x["o"] >= p["c"] and x["c"] <= p["o"] and abs(x["c"] - x["o"]) > abs(p["c"] - p["o"])


def estrella_manana(c, i):
    if i < 2:
        return False
    a, b, x = c[i - 2:i + 1]
    return (_red(a) and _body_pct(a) >= 0.5 and abs(b["c"] - b["o"]) <= 0.4 * abs(a["o"] - a["c"])
            and max(b["o"], b["c"]) <= a["c"] + 0.1 * abs(a["o"] - a["c"]) and _green(x) and x["c"] > (a["o"] + a["c"]) / 2)


def estrella_tarde(c, i):
    if i < 2:
        return False
    a, b, x = c[i - 2:i + 1]
    return (_green(a) and _body_pct(a) >= 0.5 and abs(b["c"] - b["o"]) <= 0.4 * abs(a["c"] - a["o"])
            and min(b["o"], b["c"]) >= a["c"] - 0.1 * abs(a["c"] - a["o"]) and _red(x) and x["c"] < (a["o"] + a["c"]) / 2)


def tres_soldados(c, i):
    if i < 3:
        return False
    a, b, x = c[i - 2:i + 1]
    return (all(_green(t) and _body_pct(t) >= 0.5 for t in (a, b, x)) and a["c"] < b["c"] < x["c"]
            and a["o"] <= b["o"] <= a["c"] and b["o"] <= x["o"] <= b["c"])


def tres_cuervos(c, i):
    if i < 3:
        return False
    a, b, x = c[i - 2:i + 1]
    return (all(_red(t) and _body_pct(t) >= 0.5 for t in (a, b, x)) and a["c"] > b["c"] > x["c"]
            and a["c"] <= b["o"] <= a["o"] and b["c"] <= x["o"] <= b["o"])


def harami_alcista(c, i):
    if i < 1:
        return False
    p, x = c[i - 1], c[i]
    return _red(p) and _green(x) and _body_pct(p) >= 0.5 and x["o"] >= p["c"] and x["c"] <= p["o"] and abs(x["c"] - x["o"]) < 0.6 * abs(p["o"] - p["c"])


def harami_bajista(c, i):
    if i < 1:
        return False
    p, x = c[i - 1], c[i]
    return _green(p) and _red(x) and _body_pct(p) >= 0.5 and x["o"] <= p["c"] and x["c"] >= p["o"] and abs(x["c"] - x["o"]) < 0.6 * abs(p["c"] - p["o"])


def rebote_sma21(c, i):
    """Tendencia alcista (SMA21 subiendo): la vela previa toca la SMA21 y la actual cierra verde por encima."""
    if i < 25:
        return False
    m, m1, m3 = sma(c, 21, i), sma(c, 21, i - 1), sma(c, 21, i - 3)
    return m > m3 and c[i - 1]["l"] <= m1 and c[i]["c"] > m and _green(c[i])


def rechazo_sma21(c, i):
    if i < 25:
        return False
    m, m1, m3 = sma(c, 21, i), sma(c, 21, i - 1), sma(c, 21, i - 3)
    return m < m3 and c[i - 1]["h"] >= m1 and c[i]["c"] < m and _red(c[i])


def volumen_alcista(c, i):
    if i < 20:
        return False
    av = _avg_vol(c, i)
    return av > 0 and _green(c[i]) and _body_pct(c[i]) >= 0.5 and (c[i].get("v") or 0) > 2 * av


def volumen_bajista(c, i):
    if i < 20:
        return False
    av = _avg_vol(c, i)
    return av > 0 and _red(c[i]) and _body_pct(c[i]) >= 0.5 and (c[i].get("v") or 0) > 2 * av


STRATEGIES = [  # tier: 1 = Básico, 2 = Intermedio (+5 por lado), 3 = Avanzado (resto)
    {"id": "vela_verde", "side": "BULL", "label": "Vela Verde", "fn": vela_verde, "mode": "recent", "tier": 1},
    {"id": "martillo", "side": "BULL", "label": "Martillo", "fn": martillo, "mode": "recent", "tier": 2},
    {"id": "cruce_alcista", "side": "BULL", "label": "Cruce de Medias Móviles", "fn": cruce_alcista, "mode": "recent", "tier": 2},
    {"id": "ruptura_resistencia", "side": "BULL", "label": "Ruptura de Resistencia", "fn": ruptura_resistencia, "mode": "recent", "tier": 2},
    {"id": "envolvente_alcista", "side": "BULL", "label": "Envolvente Alcista", "fn": envolvente_alcista, "mode": "recent", "tier": 2},
    {"id": "estrella_manana", "side": "BULL", "label": "Estrella de la Mañana", "fn": estrella_manana, "mode": "recent", "tier": 2},
    {"id": "tres_soldados", "side": "BULL", "label": "Tres Soldados Blancos", "fn": tres_soldados, "mode": "recent", "tier": 3},
    {"id": "harami_alcista", "side": "BULL", "label": "Harami Alcista", "fn": harami_alcista, "mode": "recent", "tier": 3},
    {"id": "rebote_sma21", "side": "BULL", "label": "Rebote en SMA 21", "fn": rebote_sma21, "mode": "recent", "tier": 3},
    {"id": "volumen_alcista", "side": "BULL", "label": "Vela con Volumen Explosivo", "fn": volumen_alcista, "mode": "recent", "tier": 3},
    {"id": "vela_roja_apertura", "side": "BEAR", "label": "Vela Roja de Apertura", "fn": vela_roja_apertura, "mode": "open", "tier": 1},
    {"id": "estrella_fugaz", "side": "BEAR", "label": "Estrella Fugaz", "fn": estrella_fugaz, "mode": "recent", "tier": 2},
    {"id": "cruce_bajista", "side": "BEAR", "label": "Cruce de Medias Móviles", "fn": cruce_bajista, "mode": "recent", "tier": 2},
    {"id": "ruptura_soporte", "side": "BEAR", "label": "Ruptura de Soporte", "fn": ruptura_soporte, "mode": "recent", "tier": 2},
    {"id": "envolvente_bajista", "side": "BEAR", "label": "Envolvente Bajista", "fn": envolvente_bajista, "mode": "recent", "tier": 2},
    {"id": "estrella_tarde", "side": "BEAR", "label": "Estrella de la Tarde", "fn": estrella_tarde, "mode": "recent", "tier": 2},
    {"id": "tres_cuervos", "side": "BEAR", "label": "Tres Cuervos Negros", "fn": tres_cuervos, "mode": "recent", "tier": 3},
    {"id": "harami_bajista", "side": "BEAR", "label": "Harami Bajista", "fn": harami_bajista, "mode": "recent", "tier": 3},
    {"id": "rechazo_sma21", "side": "BEAR", "label": "Rechazo en SMA 21", "fn": rechazo_sma21, "mode": "recent", "tier": 3},
    {"id": "volumen_bajista", "side": "BEAR", "label": "Vela con Volumen Explosivo", "fn": volumen_bajista, "mode": "recent", "tier": 3},
]
BY_ID = {s["id"]: s for s in STRATEGIES}
RECENT_BARS = 2  # una señal vale si ocurrió en las últimas 2 velas


def find_signal(strategy: dict, candles: list):
    """Índice de la vela donde se dio la señal vigente, o None."""
    n = len(candles)
    if n == 0:
        return None
    if strategy["mode"] == "open":
        last_day = _day(candles[-1])
        idx = next((k for k, x in enumerate(candles) if _day(x) == last_day), None)
        return idx if idx is not None and strategy["fn"](candles, idx) else None
    for i in range(n - 1, max(n - 1 - RECENT_BARS, -1), -1):
        if strategy["fn"](candles, i):
            return i
    return None


def scan_all(candles: list) -> dict:
    return {s["id"]: find_signal(s, candles) for s in STRATEGIES}


def all_signal_marks(candles: list, strategy_ids, last=4):
    """Marcas para el gráfico: [{i, id, side}] (las `last` más recientes por estrategia)."""
    marks = []
    for sid in strategy_ids:
        s = BY_ID.get(sid)
        if not s:
            continue
        hits = [i for i in range(len(candles)) if s["fn"](candles, i)]
        marks += [{"i": i, "id": sid, "side": s["side"]} for i in hits[-last:]]
    return marks


def sma_series(candles, n):
    return [sma(candles, n, i) for i in range(len(candles))]
