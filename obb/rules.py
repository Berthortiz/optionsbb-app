"""Constructor de estrategias por reglas (para estrategias personalizadas y señales de mentores).

Una regla = lado (BULL/BEAR) + de 1 a 6 condiciones que deben cumplirse a la vez en la misma vela (5 min).
Solo se aceptan los tipos y rangos definidos aquí: nada se ejecuta como código.
"""
import json

MAX_COND = 6
RECENT_BARS = 2


class RuleError(ValueError):
    pass


def _int(v, name, lo, hi):
    try:
        x = int(v)
    except (TypeError, ValueError):
        raise RuleError(f"{name} debe ser un número entero")
    if not lo <= x <= hi:
        raise RuleError(f"{name} debe estar entre {lo} y {hi}")
    return x


def _flt(v, name, lo, hi):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise RuleError(f"{name} debe ser un número")
    if not lo <= x <= hi:
        raise RuleError(f"{name} debe estar entre {lo} y {hi}")
    return x


def _choice(v, name, opts):
    if v not in opts:
        raise RuleError(f"{name} no es válido")
    return v


# tipo → (etiqueta, validador)
def _v_sma_cross(c):
    f, s = _int(c.get("fast"), "Media rápida", 2, 100), _int(c.get("slow"), "Media lenta", 3, 300)
    if f >= s:
        raise RuleError("La media rápida debe ser menor que la lenta")
    return {"fast": f, "slow": s, "dir": _choice(c.get("dir"), "Dirección", ("up", "down"))}


def _v_price_sma(c):
    return {"n": _int(c.get("n"), "Periodo de la media", 2, 300), "dir": _choice(c.get("dir"), "Posición", ("above", "below"))}


def _v_breakout(c):
    return {"n": _int(c.get("n"), "Velas", 2, 200), "dir": _choice(c.get("dir"), "Dirección", ("up", "down")),
            "vol_mult": _flt(c.get("vol_mult", 0), "Volumen de confirmación", 0, 20)}


def _v_golden(c):
    f, s = _int(c.get("fast", 50), "Media rápida", 2, 100), _int(c.get("slow", 200), "Media lenta", 3, 300)
    if f >= s:
        raise RuleError("La media rápida debe ser menor que la lenta")
    return {"fast": f, "slow": s, "dir": _choice(c.get("dir"), "Cruce", ("golden", "death"))}


def _v_doji(c):
    return {"max_body_pct": _flt(c.get("max_body_pct", 10), "Cuerpo máximo %", 0.5, 30),
            "kind": _choice(c.get("kind", "any"), "Tipo de doji", ("any", "dragonfly", "gravestone"))}


def _v_engulf(c):
    return {"dir": _choice(c.get("dir"), "Envolvente", ("bull", "bear")), "trend_bars": _int(c.get("trend_bars", 0), "Tendencia previa", 0, 20)}


def _v_candle(c):
    return {"color": _choice(c.get("color"), "Color", ("green", "red")), "min_body_pct": _flt(c.get("min_body_pct", 0), "Cuerpo mínimo %", 0, 100)}


def _v_streak(c):
    return {"n": _int(c.get("n"), "Velas seguidas", 1, 10), "color": _choice(c.get("color"), "Color", ("green", "red"))}


def _v_volume(c):
    return {"mult": _flt(c.get("mult"), "Veces el volumen promedio", 1, 20), "n": _int(c.get("n", 20), "Promedio de", 5, 100)}


def _v_rsi(c):
    return {"n": _int(c.get("n", 14), "Periodo RSI", 2, 50), "op": _choice(c.get("op"), "Comparación", ("lt", "gt")),
            "value": _flt(c.get("value"), "Nivel RSI", 0, 100)}


def _v_pct(c):
    return {"bars": _int(c.get("bars"), "Velas", 1, 80), "op": _choice(c.get("op"), "Comparación", ("lt", "gt")),
            "pct": _flt(c.get("pct"), "Cambio %", -50, 50)}


VALIDATORS = {"sma_cross": _v_sma_cross, "price_sma": _v_price_sma, "breakout": _v_breakout, "candle": _v_candle,
              "streak": _v_streak, "volume_spike": _v_volume, "rsi": _v_rsi, "pct_move": _v_pct,
              "golden_cross": _v_golden, "doji": _v_doji, "engulfing": _v_engulf}


def validate(rule) -> dict:
    if not isinstance(rule, dict):
        raise RuleError("Regla no válida")
    side = _choice(rule.get("side"), "Lado", ("BULL", "BEAR"))
    conds = rule.get("conditions")
    if not isinstance(conds, list) or not 1 <= len(conds) <= MAX_COND:
        raise RuleError(f"Agrega entre 1 y {MAX_COND} condiciones")
    out = []
    for c in conds:
        if not isinstance(c, dict) or c.get("type") not in VALIDATORS:
            raise RuleError("Tipo de condición no válido")
        out.append({"type": c["type"], **VALIDATORS[c["type"]](c)})
    return {"side": side, "conditions": out}


def loads(text) -> dict:
    try:
        return validate(json.loads(text))
    except (ValueError, TypeError) as e:
        raise RuleError(str(e))


# ---------------------------------------------------------------- evaluación
def _sma(c, n, i):
    return sum(x["c"] for x in c[i + 1 - n:i + 1]) / n if i + 1 >= n else None


def _rsi(c, n, i):
    if i < n:
        return None
    g = l = 0.0
    for k in range(i - n + 1, i + 1):
        d = c[k]["c"] - c[k - 1]["c"]
        g, l = g + max(d, 0), l + max(-d, 0)
    if g + l == 0:
        return 50.0
    return 100.0 if l == 0 else 100 - 100 / (1 + g / l)


def _cond(k, c, i):
    t, x = k["type"], c[i]
    if t == "sma_cross":
        if i < k["slow"]:
            return False
        a, b, a0, b0 = _sma(c, k["fast"], i), _sma(c, k["slow"], i), _sma(c, k["fast"], i - 1), _sma(c, k["slow"], i - 1)
        return (a > b and a0 <= b0) if k["dir"] == "up" else (a < b and a0 >= b0)
    if t == "price_sma":
        m = _sma(c, k["n"], i)
        return m is not None and ((x["c"] > m) if k["dir"] == "above" else (x["c"] < m))
    if t == "breakout":
        if i < k["n"]:
            return False
        brk = x["c"] > max(y["h"] for y in c[i - k["n"]:i]) if k["dir"] == "up" else x["c"] < min(y["l"] for y in c[i - k["n"]:i])
        vm = k.get("vol_mult") or 0
        if brk and vm > 0:
            av = sum((y.get("v") or 0) for y in c[max(0, i - 20):i]) / max(1, min(20, i))
            return av > 0 and (x.get("v") or 0) >= vm * av
        return brk
    if t == "golden_cross":
        if i < k["slow"]:
            return False
        a, b, a0, b0 = _sma(c, k["fast"], i), _sma(c, k["slow"], i), _sma(c, k["fast"], i - 1), _sma(c, k["slow"], i - 1)
        return (a > b and a0 <= b0) if k["dir"] == "golden" else (a < b and a0 >= b0)
    if t == "doji":
        rng = x["h"] - x["l"]
        if rng <= 0:
            return False
        body, top, bot = abs(x["c"] - x["o"]), max(x["o"], x["c"]), min(x["o"], x["c"])
        if body / rng * 100 > k["max_body_pct"]:
            return False
        up, lo = (x["h"] - top) / rng, (bot - x["l"]) / rng
        if k["kind"] == "dragonfly":
            return lo >= 0.6 and up <= 0.1
        if k["kind"] == "gravestone":
            return up >= 0.6 and lo <= 0.1
        return True
    if t == "engulfing":
        if i < 1:
            return False
        p = c[i - 1]
        tb = k.get("trend_bars", 0)
        if k["dir"] == "bull":
            ok = p["c"] < p["o"] and x["c"] > x["o"] and x["o"] <= p["c"] and x["c"] >= p["o"] and (x["c"] - x["o"]) > (p["o"] - p["c"])
            return ok and (tb == 0 or (i - tb >= 0 and c[i - 1]["c"] < c[i - tb]["c"]))
        ok = p["c"] > p["o"] and x["c"] < x["o"] and x["o"] >= p["c"] and x["c"] <= p["o"] and (x["o"] - x["c"]) > (p["c"] - p["o"])
        return ok and (tb == 0 or (i - tb >= 0 and c[i - 1]["c"] > c[i - tb]["c"]))
    if t == "candle":
        rng = x["h"] - x["l"]
        body = abs(x["c"] - x["o"])
        ok = x["c"] > x["o"] if k["color"] == "green" else x["c"] < x["o"]
        return ok and rng > 0 and body / rng * 100 >= k["min_body_pct"]
    if t == "streak":
        if i < k["n"]:
            return False
        return all((y["c"] > y["o"]) if k["color"] == "green" else (y["c"] < y["o"]) for y in c[i - k["n"] + 1:i + 1])
    if t == "volume_spike":
        if i < k["n"]:
            return False
        av = sum((y.get("v") or 0) for y in c[i - k["n"]:i]) / k["n"]
        return av > 0 and (x.get("v") or 0) >= k["mult"] * av
    if t == "rsi":
        r = _rsi(c, k["n"], i)
        return r is not None and (r < k["value"] if k["op"] == "lt" else r > k["value"])
    if t == "pct_move":
        if i < k["bars"]:
            return False
        base = c[i - k["bars"]]["c"]
        if not base:
            return False
        ch = (x["c"] / base - 1) * 100
        return ch < k["pct"] if k["op"] == "lt" else ch > k["pct"]
    return False


def at(rule, candles, i) -> bool:
    return all(_cond(k, candles, i) for k in rule["conditions"])


def find_signal(rule, candles):
    n = len(candles)
    for i in range(n - 1, max(n - 1 - RECENT_BARS, -1), -1):
        if at(rule, candles, i):
            return i
    return None


def describe(rule) -> list:
    D = {"up": "al alza", "down": "a la baja", "above": "sobre", "below": "bajo", "green": "verde", "red": "roja", "lt": "menor que", "gt": "mayor que"}
    out = []
    for k in rule["conditions"]:
        t = k["type"]
        if t == "sma_cross":
            out.append(f"SMA {k['fast']} cruza {D[k['dir']]} la SMA {k['slow']}")
        elif t == "price_sma":
            out.append(f"Precio {D[k['dir']]} la SMA {k['n']}")
        elif t == "breakout":
            vm = k.get("vol_mult") or 0
            out.append(f"Breakout {'alcista' if k['dir'] == 'up' else 'bajista'}: cierre rompe el {'máximo' if k['dir'] == 'up' else 'mínimo'} de {k['n']} velas" + (f" con volumen ≥ {vm:g}× el promedio" if vm else ""))
        elif t == "golden_cross":
            out.append(f"{'Cruz dorada' if k['dir'] == 'golden' else 'Cruz de la muerte'}: SMA {k['fast']} cruza {'sobre' if k['dir'] == 'golden' else 'bajo'} la SMA {k['slow']}")
        elif t == "doji":
            nm = {"any": "Doji", "dragonfly": "Doji libélula", "gravestone": "Doji lápida"}[k["kind"]]
            out.append(f"{nm} (cuerpo ≤ {k['max_body_pct']:g}% del rango)")
        elif t == "engulfing":
            out.append(f"Vela envolvente {'alcista' if k['dir'] == 'bull' else 'bajista'}" + (f" tras {k['trend_bars']} velas en {'baja' if k['dir'] == 'bull' else 'alza'}" if k.get("trend_bars") else ""))
        elif t == "candle":
            out.append(f"Vela {D[k['color']]} con cuerpo ≥ {k['min_body_pct']:g}% del rango")
        elif t == "streak":
            out.append(f"{k['n']} velas {D[k['color']]}s seguidas")
        elif t == "volume_spike":
            out.append(f"Volumen ≥ {k['mult']:g}× el promedio de {k['n']} velas")
        elif t == "rsi":
            out.append(f"RSI({k['n']}) {D[k['op']]} {k['value']:g}")
        elif t == "pct_move":
            out.append(f"Cambio en {k['bars']} velas {D[k['op']]} {k['pct']:g}%")
    return out
