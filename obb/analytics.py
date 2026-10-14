"""Cambios por periodo, efectividad de estrategias por temporalidad (backtest simple) y resumen por acción."""
import math
import statistics
from datetime import datetime

from . import clock, library, rules, strategies

PERIODS = [("0", "Hoy"), ("7", "7 días"), ("15", "15 días"), ("30", "30 días"), ("90", "90 días"), ("360", "360 días")]
PERIOD_KEYS = [k for k, _ in PERIODS]
DEFAULT_PERIODS = ["0"]
TFS = [("5m", "5 min", 1), ("15m", "15 min", 3), ("30m", "30 min", 6), ("1h", "1 hora", 12), ("1d", "Diario", 0)]
TF_KEYS = [t[0] for t in TFS]
HORIZON = 5      # el resultado de cada señal se mide 5 velas después
MIN_N = 20       # mínimo de señales para entrar al ranking


# ---------------------------------------------------------------- velas
def resample(c5: list, factor: int) -> list:
    """Agrupa velas de 5 min en velas de factor×5 min, ancladas a la apertura (9:30 ET) de cada día."""
    if factor <= 1:
        return c5
    out, key, cur = [], None, None
    for x in c5:
        d = datetime.fromtimestamp(x["t"], clock.ET)
        mins = (d.hour * 60 + d.minute) - (9 * 60 + 30)
        k = (d.date(), max(mins, 0) // (5 * factor))
        if k != key:
            if cur:
                out.append(cur)
            key, cur = k, {"t": x["t"], "o": x["o"], "h": x["h"], "l": x["l"], "c": x["c"], "v": x.get("v") or 0}
        else:
            cur["h"], cur["l"], cur["c"] = max(cur["h"], x["h"]), min(cur["l"], x["l"]), x["c"]
            cur["v"] += x.get("v") or 0
    if cur:
        out.append(cur)
    return out


def period_changes(daily: list, price: float, today_pct, now_t: float) -> dict:
    """% de cambio de hoy y de N días calendario (contra el último cierre en o antes de esa fecha)."""
    out = {"0": today_pct}
    for k in PERIOD_KEYS[1:]:
        cut = now_t - int(k) * 86400
        ref = None
        for x in daily:
            if x["t"] <= cut:
                ref = x["c"]
            else:
                break
        if ref is None and daily and now_t - daily[0]["t"] >= 0.95 * int(k) * 86400:
            ref = daily[0]["c"]  # el historial de 1 año queda un poco corto: usamos su primera vela
        out[k] = (price / ref - 1) * 100 if ref else None
    return out


# ---------------------------------------------------------------- detectores
def detectors(include_catalog=True) -> list:
    out = [{"key": s["id"], "label": s["label"], "side": s["side"], "kind": "core", "tier": s["tier"],
            "fn": s["fn"], "active": (lambda c, s=s: strategies.find_signal(s, c) is not None)} for s in strategies.STRATEGIES]
    if include_catalog:
        for c in library.list_catalog():
            r = c["rule"]
            out.append({"key": f"cat:{c['id']}", "label": c["name"], "side": c["side"], "kind": "cat", "tier": 3,
                        "fn": (lambda cs, i, r=r: rules.at(r, cs, i)), "active": (lambda cs, r=r: rules.find_signal(r, cs) is not None)})
    return out


def backtest(candles, fn, side, horizon=HORIZON):
    """Resultados (%, a favor de la señal) de cada señal, sin traslapar operaciones."""
    res, n, i = [], len(candles), 0
    while i < n - horizon:
        try:
            hit = fn(candles, i)
        except Exception:
            hit = False
        if hit and candles[i]["c"]:
            r = (candles[i + horizon]["c"] / candles[i]["c"] - 1) * 100
            res.append(r if side == "BULL" else -r)
            i += horizon
        else:
            i += 1
    return res


def _agg():
    return {"n": 0, "wins": 0, "sum": 0.0, "gw": 0.0, "gl": 0.0, "by": {}, "active": []}


def _add(a, results):
    for r in results:
        a["n"] += 1
        a["sum"] += r
        if r > 0:
            a["wins"] += 1
            a["gw"] += r
        else:
            a["gl"] += -r


def compute(symbols, get_5m, get_daily) -> dict:
    """Backtest de todas las estrategias en todas las temporalidades. get_5m/get_daily: sym -> velas."""
    dets = detectors()
    tfs = {t: {d["key"]: _agg() for d in dets} for t in TF_KEYS}
    for sym in symbols:
        try:
            c5, cd = get_5m(sym), get_daily(sym)
        except Exception:
            continue
        for tf, _, f in TFS:
            cs = cd if tf == "1d" else resample(c5, f)
            if len(cs) < 30:
                continue
            for d in dets:
                a = tfs[tf][d["key"]]
                res = backtest(cs, d["fn"], d["side"])
                if res:
                    _add(a, res)
                    a["by"][sym] = [len(res), sum(1 for r in res if r > 0), sum(res)]
                try:
                    if d["active"](cs):
                        a["active"].append(sym)
                except Exception:
                    pass
    return {"tfs": tfs, "dets": {d["key"]: {"label": d["label"], "side": d["side"], "kind": d["kind"], "tier": d["tier"]} for d in dets}}


def _stats(a):
    n = a["n"]
    return {"n": n, "win_rate": a["wins"] / n * 100 if n else None, "avg": a["sum"] / n if n else None,
            "profit_factor": (a["gw"] / a["gl"]) if a["gl"] > 0 else (None if not a["gw"] else 99.0)}


def ranking(eff: dict, tf: str, allowed) -> dict:
    """Ranking de una temporalidad. allowed: conjunto de claves visibles para el plan (None = todas)."""
    if not eff or tf not in eff["tfs"]:
        return {"rows": [], "few": []}
    rows, few = [], []
    for key, a in eff["tfs"][tf].items():
        meta = eff["dets"][key]
        if allowed is not None and key not in allowed:
            continue
        s = _stats(a)
        best = sorted(((sym, v) for sym, v in a["by"].items() if v[0] >= 3), key=lambda kv: kv[1][2] / kv[1][0], reverse=True)[:6]
        row = {"key": key, "label": meta["label"], "side": meta["side"], "kind": meta["kind"], **s,
               "active": sorted(a["active"]),
               "best": [{"symbol": sym, "n": v[0], "win_rate": v[1] / v[0] * 100, "avg": v[2] / v[0]} for sym, v in best]}
        (rows if a["n"] >= MIN_N else few).append(row)
    rows.sort(key=lambda r: (r["avg"], r["win_rate"]), reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return {"rows": rows, "few": few, "min_n": MIN_N, "horizon": HORIZON}


def best_for_symbol(eff: dict, sym: str, tf: str, allowed, top=4) -> list:
    out = []
    if not eff or tf not in eff["tfs"]:
        return out
    for key, a in eff["tfs"][tf].items():
        if allowed is not None and key not in allowed:
            continue
        v = a["by"].get(sym)
        if v and v[0] >= 3:
            out.append({"key": key, "label": eff["dets"][key]["label"], "side": eff["dets"][key]["side"], "n": v[0],
                        "win_rate": v[1] / v[0] * 100, "avg": v[2] / v[0], "active": sym in a["active"]})
    out.sort(key=lambda r: r["avg"], reverse=True)
    return out[:top]


# ---------------------------------------------------------------- resumen por acción
def _rsi(closes, n=14):
    if len(closes) <= n:
        return None
    g = l = 0.0
    for a, b in zip(closes[-n - 1:-1], closes[-n:]):
        d = b - a
        g, l = g + max(d, 0), l + max(-d, 0)
    return 100.0 if l == 0 else 100 - 100 / (1 + g / l)


def _sma(closes, n):
    return sum(closes[-n:]) / n if len(closes) >= n else None


def tf_trend(cs):
    cl = [x["c"] for x in cs]
    m9, m21 = _sma(cl, 9), _sma(cl, 21)
    if m9 is None or m21 is None:
        return {"trend": None, "rsi": _rsi(cl)}
    price = cl[-1]
    trend = "alcista" if price > m21 and m9 > m21 else "bajista" if price < m21 and m9 < m21 else "lateral"
    return {"trend": trend, "rsi": _rsi(cl), "sma9": m9, "sma21": m21, "price": price}


def summary(daily: list, quote: dict, now_t: float, vol_info=None) -> dict:
    cl = [x["c"] for x in daily]
    if len(cl) < 5:
        return {}
    price = (quote or {}).get("price") or cl[-1]
    rets = [cl[i] / cl[i - 1] - 1 for i in range(1, len(cl)) if cl[i - 1]]
    peak, mdd = cl[0], 0.0
    for p in cl:
        peak = max(peak, p)
        mdd = max(mdd, (peak - p) / peak)
    hi, lo = max(x["h"] for x in daily), min(x["l"] for x in daily)
    v20 = [x.get("v") or 0 for x in daily[-21:-1]]
    avg_v = sum(v20) / len(v20) if v20 else 0
    s50, s200 = _sma(cl, 50), _sma(cl, 200)
    out = {
        "price": price, "changes": period_changes(daily, price, (quote or {}).get("change_pct"), now_t),
        "hi52": hi, "lo52": lo, "from_hi_pct": (price / hi - 1) * 100, "from_lo_pct": (price / lo - 1) * 100,
        "range_pos": (price - lo) / (hi - lo) * 100 if hi > lo else None,
        "vol_ann": statistics.pstdev(rets) * math.sqrt(252) * 100 if len(rets) > 2 else None,
        "max_dd": mdd * 100, "rsi14": _rsi(cl), "sma20": _sma(cl, 20), "sma50": s50, "sma200": s200,
        "trend_long": None if s50 is None else ("alcista" if price > s50 and (s200 is None or s50 > s200) else "bajista" if price < s50 and (s200 is None or s50 < s200) else "lateral"),
        "avg_vol20": avg_v, "vol_today": (quote or {}).get("volume"),
        "spark": [round(x, 2) for x in cl[-90:]],
        "days": len(cl),
    }
    if vol_info:
        out["options"] = vol_info
    return out
