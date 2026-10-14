"""Calculadora de opciones (Black-Scholes) y exposición gamma (GEX). Solo biblioteca estándar."""
import math

RATE = 0.045


class CalcError(ValueError):
    pass


def _N(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _n(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def _d(S, K, T, v, r):
    return (math.log(S / K) + (r + 0.5 * v * v) * T) / (v * math.sqrt(T))


def price(cp, S, K, T, v, r=RATE):
    if T <= 0 or v <= 0:
        return max(S - K, 0.0) if cp == "C" else max(K - S, 0.0)
    d1 = _d(S, K, T, v, r); d2 = d1 - v * math.sqrt(T)
    if cp == "C":
        return S * _N(d1) - K * math.exp(-r * T) * _N(d2)
    return K * math.exp(-r * T) * _N(-d2) - S * _N(-d1)


def greeks(cp, S, K, T, v, r=RATE):
    """delta, gamma, theta (por día), vega (por 1 % de volatilidad)."""
    if T <= 0 or v <= 0:
        return {"delta": (1.0 if S > K else 0.0) if cp == "C" else (-1.0 if S < K else 0.0), "gamma": 0.0, "theta": 0.0, "vega": 0.0}
    d1 = _d(S, K, T, v, r); d2 = d1 - v * math.sqrt(T); sq = math.sqrt(T)
    delta = _N(d1) if cp == "C" else _N(d1) - 1
    gamma = _n(d1) / (S * v * sq)
    t1 = -S * _n(d1) * v / (2 * sq)
    theta = (t1 - r * K * math.exp(-r * T) * _N(d2)) if cp == "C" else (t1 + r * K * math.exp(-r * T) * _N(-d2))
    return {"delta": delta, "gamma": gamma, "theta": theta / 365.0, "vega": S * _n(d1) * sq / 100.0}


# ---------------------------------------------------------------- plantillas
def template_legs(name, S, step=None, dte=30, iv=0.35):
    """Patas de una estrategia estándar alrededor del precio S. Cada pata: type C/P/S, side +1/-1, strike, qty, dte."""
    step = step or (0.5 if S < 20 else 1 if S < 50 else 2.5 if S < 150 else 5 if S < 400 else 10)
    atm = round(S / step) * step
    c = lambda t, side, k, q=1: {"type": t, "side": side, "strike": round(k, 2), "qty": q, "dte": dte}
    T = {
        "long_call": [c("C", 1, atm)],
        "long_put": [c("P", 1, atm)],
        "covered_call": [c("S", 1, S, 100), c("C", -1, atm + 2 * step)],
        "cash_secured_put": [c("P", -1, atm - 2 * step)],
        "protective_put": [c("S", 1, S, 100), c("P", 1, atm - 2 * step)],
        "bull_call_spread": [c("C", 1, atm), c("C", -1, atm + 2 * step)],
        "bear_put_spread": [c("P", 1, atm), c("P", -1, atm - 2 * step)],
        "straddle": [c("C", 1, atm), c("P", 1, atm)],
        "iron_condor": [c("P", 1, atm - 4 * step), c("P", -1, atm - 2 * step), c("C", -1, atm + 2 * step), c("C", 1, atm + 4 * step)],
    }
    if name not in T:
        raise CalcError("Plantilla desconocida")
    return T[name]


TEMPLATES = ["long_call", "long_put", "covered_call", "cash_secured_put", "protective_put", "bull_call_spread", "bear_put_spread", "straddle", "iron_condor"]
MAX_LEGS = 6


def analyze(S, legs, iv=0.35, r=RATE, days_ahead=0):
    """Resultado de una combinación de patas.
    Patas de opción: premium opcional (si falta se estima con Black-Scholes y la vol. dada). Las acciones usan strike = precio de compra.
    Devuelve curvas al vencimiento y 'hoy' (+days_ahead), puntos de equilibrio, máximos, griegas y probabilidad de ganancia."""
    if not (S > 0 and 0.01 <= iv <= 5):
        raise CalcError("Precio o volatilidad no válidos")
    if not legs or len(legs) > MAX_LEGS:
        raise CalcError(f"Usa entre 1 y {MAX_LEGS} patas")
    L = []
    for g in legs:
        t = g.get("type")
        if t not in ("C", "P", "S") or g.get("side") not in (1, -1):
            raise CalcError("Pata no válida")
        q = int(g.get("qty") or 1)
        if not 1 <= q <= 10000:
            raise CalcError("Cantidad no válida")
        K = float(g.get("strike") or 0)
        if K <= 0:
            raise CalcError("Strike no válido")
        dte = max(int(g.get("dte") or 30), 0)
        viv = float(g.get("iv") or iv)
        if t == "S":
            L.append({"type": "S", "side": g["side"], "K": K, "q": q, "T": 0.0, "dte": 0, "iv": viv, "prem": 0.0, "mult": 1})
            continue
        T = dte / 365.0
        prem = g.get("premium")
        prem = float(prem) if prem not in (None, "") else price(t, S, K, T, viv, r)
        L.append({"type": t, "side": g["side"], "K": K, "q": q, "T": T, "dte": dte, "iv": viv, "prem": prem, "mult": 100})
    Tmax = max((x["T"] for x in L), default=0.0)
    Tmin_opt = min((x["T"] for x in L if x["type"] != "S"), default=0.0)   # el payoff se evalúa al primer vencimiento
    exp_T = Tmin_opt

    def pnl(s, t_elapsed):
        tot = 0.0
        for x in L:
            if x["type"] == "S":
                tot += x["side"] * x["q"] * (s - x["K"])
            else:
                rem = x["T"] - t_elapsed
                val = price(x["type"], s, x["K"], rem, x["iv"], r) if rem > 1e-9 else (max(s - x["K"], 0) if x["type"] == "C" else max(x["K"] - s, 0))
                tot += x["side"] * x["q"] * x["mult"] * (val - x["prem"])
        return tot

    lo, hi = S * 0.6, S * 1.4
    N = 81
    xs = [lo + (hi - lo) * i / (N - 1) for i in range(N)]
    at_exp = [pnl(s, exp_T) for s in xs]
    t_today = min(days_ahead / 365.0, exp_T)
    today = [pnl(s, t_today) for s in xs]
    # equilibrios (cruces de cero al vencimiento)
    be = []
    for i in range(N - 1):
        a, b = at_exp[i], at_exp[i + 1]
        if a == 0:
            be.append(xs[i])
        elif a * b < 0:
            be.append(xs[i] + (xs[i + 1] - xs[i]) * (-a) / (b - a))
    slope_hi = (at_exp[-1] - at_exp[-2]) / (xs[-1] - xs[-2])
    slope_lo = (at_exp[1] - at_exp[0]) / (xs[1] - xs[0])
    zero = pnl(1e-6, exp_T)       # la acción no puede valer menos de 0
    mx, mn = max(max(at_exp), zero), min(min(at_exp), zero)
    max_profit = None if slope_hi > 1e-6 else mx          # None = ilimitada
    max_loss = None if slope_hi < -1e-6 else mn
    net = sum(x["side"] * x["q"] * x["mult"] * x["prem"] for x in L if x["type"] != "S")   # >0 débito pagado
    g = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}
    for x in L:
        if x["type"] == "S":
            g["delta"] += x["side"] * x["q"]
            continue
        gg = greeks(x["type"], S, x["K"], x["T"], x["iv"], r)
        for k in g:
            g[k] += x["side"] * x["q"] * x["mult"] * gg[k]
    # probabilidad de ganancia al vencimiento (log-normal, vol. media de las patas)
    prob = None
    if exp_T > 0:
        v = sum(x["iv"] for x in L) / len(L)
        sd = v * math.sqrt(exp_T)
        mu = math.log(S) + (r - 0.5 * v * v) * exp_T
        fine = [S * 0.2 + S * 1.8 * i / 800 for i in range(801)]
        pr, p_prev = 0.0, 0.0
        for s in fine:
            cdf = _N((math.log(s) - mu) / sd)
            if pnl(s, exp_T) > 0:
                pr += cdf - p_prev
            p_prev = cdf
        prob = max(0.0, min(1.0, pr))
    return {"spot": S, "x": [round(v, 2) for v in xs], "expiry": [round(v, 2) for v in at_exp], "today": [round(v, 2) for v in today],
            "breakevens": [round(b, 2) for b in be], "max_profit": None if max_profit is None else round(max_profit, 2),
            "max_loss": None if max_loss is None else round(max_loss, 2), "net": round(net, 2),
            "greeks": {k: round(v, 4) for k, v in g.items()}, "prob_profit": None if prob is None else round(prob, 4),
            "legs": [{"type": x["type"], "side": x["side"], "strike": x["K"], "qty": x["q"], "dte": x["dte"], "premium": round(x["prem"], 4), "iv": x["iv"]} for x in L],
            "days_ahead": days_ahead}


# ---------------------------------------------------------------- GEX
def gex(spot, contracts, expiry=None, band=0.15):
    """Exposición gamma por strike. Convención habitual: los dealers están largos las calls y cortos las puts de los clientes.
    GEX por strike = gamma * OI * 100 * precio² * 1 %  (en dólares por cada 1 % de movimiento).
    Si el contrato no trae gamma se calcula con Black-Scholes y su volatilidad implícita."""
    rows = {}
    expiries = sorted({c["expiry"] for c in contracts})
    for c in contracts:
        if expiry and expiry != "all" and c["expiry"] != expiry:
            continue
        K = c["strike"]
        if abs(K / spot - 1) > band:
            continue
        gm = c.get("gamma")
        if gm is None:
            dte = c.get("dte")
            T = max((dte if dte is not None else 1), 0.5) / 365.0
            gm = greeks(c["cp"], spot, K, T, c.get("iv") or 0.35)["gamma"]
        val = gm * c["oi"] * 100 * spot * spot * 0.01
        r = rows.setdefault(K, {"strike": K, "call": 0.0, "put": 0.0, "call_oi": 0, "put_oi": 0})
        if c["cp"] == "C":
            r["call"] += val; r["call_oi"] += c["oi"]
        else:
            r["put"] -= val; r["put_oi"] += c["oi"]
    out = sorted(rows.values(), key=lambda r: r["strike"])
    if not out:
        raise CalcError("Sin datos de opciones para ese vencimiento")
    for r in out:
        r["net"] = r["call"] + r["put"]
    call_wall = max(out, key=lambda r: r["call"])
    put_wall = min(out, key=lambda r: r["put"])
    flip, cum = None, 0.0
    for i, r in enumerate(out):
        prev = cum; cum += r["net"]
        if i and prev * cum < 0:
            flip = round(out[i - 1]["strike"] + (r["strike"] - out[i - 1]["strike"]) * (-prev) / (cum - prev), 2)
    total = sum(r["net"] for r in out)
    rnd = lambda v: round(v, 0)
    return {"spot": spot, "expiry": expiry or "all", "expiries": expiries, "call_wall": call_wall["strike"], "put_wall": put_wall["strike"], "flip": flip,
            "net_gex": rnd(total), "regime": "positive" if total > 0 else "negative",
            "rows": [{"strike": r["strike"], "call": rnd(r["call"]), "put": rnd(r["put"]), "net": rnd(r["net"]), "call_oi": r["call_oi"], "put_oi": r["put_oi"]} for r in out]}
