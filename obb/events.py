"""Earnings (movimiento del precio en cada reporte) y dividendos. Todo automático:
 - Fechas de earnings: Finnhub (clave FINNHUB_API_KEY, plan gratuito).  Historial de dividendos: Alpha Vantage (ALPHAVANTAGE_API_KEY).
 - Los movimientos se CALCULAN con las velas diarias de Schwab: nadie los captura a mano.
 - En modo DEMO se generan fechas simuladas.  Las llamadas a Finnhub / Alpha Vantage no se han podido probar sin acceso a internet real."""
import json
import statistics
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

from . import clock, config, db, providers

TTL = 12 * 3600


def _cached(key, ttl, fn):
    raw = db.kv_get("ev:" + key, "")
    if raw:
        try:
            ts, data = json.loads(raw)
            if time.time() - ts < ttl:
                return data
        except ValueError:
            pass
    data = fn()
    db.kv_set("ev:" + key, json.dumps([time.time(), data]))
    return data


def _get_json(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "optionsbb"}), timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:
        raise providers.ProviderError(f"No pude consultar el servicio de datos externo ({type(e).__name__})")


def _dates(candles):
    return [datetime.fromtimestamp(c["t"], clock.ET).date() for c in candles]


# ---------------------------------------------------------------- earnings
def _calendar(sym, demo, candles):
    if demo:
        ds = _dates(candles)
        out, i = [], len(ds) - 20
        k = 0
        while i > 5:
            est = round(1.0 + 0.04 * (14 - k) + (hash(sym) % 7) / 20, 2)  # EPS simulado (solo DEMO)
            act = round(est * (1 + (((k * 7 + len(sym) * 3) % 11) - 4) / 60), 2)
            out.append({"date": ds[i].isoformat(), "hour": "amc" if (k + len(sym)) % 2 else "bmo", "eps": act, "eps_est": est})
            i -= 63; k += 1
        return out
    if not config.FINNHUB_KEY:
        raise providers.ProviderError("Falta la clave FINNHUB_API_KEY para traer las fechas de earnings (gratuita en finnhub.io). Configúrala en el servidor.")
    frm = (date.today() - timedelta(days=365 * 5)).isoformat()
    to = (date.today() + timedelta(days=120)).isoformat()
    q = urllib.parse.urlencode({"from": frm, "to": to, "symbol": sym, "token": config.FINNHUB_KEY})
    data = _cached(f"cal:{sym}", TTL, lambda: _get_json("https://finnhub.io/api/v1/calendar/earnings?" + q))
    return [{"date": e.get("date"), "hour": e.get("hour") or "", "eps": e.get("epsActual"), "eps_est": e.get("epsEstimate")}
            for e in (data.get("earningsCalendar") or []) if e.get("date")]


def earnings(sym, provider, candles):
    """candles: velas diarias de ~5 años."""
    demo = provider.name == "demo"
    cal = _calendar(sym, demo, candles)
    ds = _dates(candles)
    today = date.today() if not demo else ds[-1]
    rows, upcoming = [], None
    for e in sorted(cal, key=lambda x: x["date"], reverse=True):
        d = date.fromisoformat(e["date"])
        if d >= today and not (d == today and e["hour"] == "bmo"):
            upcoming = {"date": e["date"], "hour": e["hour"]}
            continue
        idx = next((i for i, x in enumerate(ds) if x >= d), None)
        if idx is None:
            continue
        if e["hour"] == "amc":
            idx += 1
        if idx < 1 or idx >= len(candles):
            continue
        prev, cur = candles[idx - 1], candles[idx]
        nxt = candles[idx + 1] if idx + 1 < len(candles) else None
        pc = prev["c"]
        rows.append({"date": e["date"], "hour": e["hour"], "react_date": ds[idx].isoformat(), "prev_close": round(pc, 2), "open": round(cur["o"], 2), "close": round(cur["c"], 2),
                     "gap_pct": round((cur["o"] / pc - 1) * 100, 2), "day_pct": round((cur["c"] / pc - 1) * 100, 2),
                     "range_pct": round((cur["h"] - cur["l"]) / pc * 100, 2), "next_pct": None if not nxt else round((nxt["c"] / cur["c"] - 1) * 100, 2),
                     "eps": e["eps"], "eps_est": e["eps_est"]})
    rows = rows[:12]  # los últimos 12 reportes
    for r in rows:
        r["surprise_pct"] = round((r["eps"] / r["eps_est"] - 1) * 100, 1) if (r.get("eps") is not None and r.get("eps_est")) else None
    s = None
    if rows:
        d_ = [r["day_pct"] for r in rows]
        s = {"count": len(rows), "avg_abs_day": round(statistics.mean(abs(x) for x in d_), 2), "avg_abs_gap": round(statistics.mean(abs(r["gap_pct"]) for r in rows), 2),
             "median_abs_day": round(statistics.median(abs(x) for x in d_), 2), "up": sum(1 for x in d_ if x > 0), "down": sum(1 for x in d_ if x < 0),
             "best": max(d_), "worst": min(d_), "avg_range": round(statistics.mean(r["range_pct"] for r in rows), 2)}
    return {"symbol": sym, "rows": rows, "summary": s, "trend": _trend(rows), "hist": _hist(rows), "upcoming": upcoming, "demo": demo}


def _slope(ys):
    """Pendiente de la recta de mínimos cuadrados (cronológico)."""
    n = len(ys)
    if n < 3:
        return None
    mx, my = (n - 1) / 2, sum(ys) / n
    den = sum((i - mx) ** 2 for i in range(n))
    return sum((i - mx) * (y - my) for i, y in enumerate(ys)) / den if den else 0.0


def _trend(rows):
    """Tendencia de los reportes (rows viene del más reciente al más antiguo)."""
    if len(rows) < 4:
        return None
    chron = list(reversed(rows))
    ab = [abs(r["day_pct"]) for r in chron]
    recent, older = ab[-4:], ab[:-4]
    r_avg = statistics.mean(recent)
    o_avg = statistics.mean(older) if older else None
    sl = _slope(ab)
    ma3 = [round(statistics.mean(ab[max(0, i - 2):i + 1]), 2) for i in range(len(ab))]
    ups = [1 if r["day_pct"] > 0 else 0 for r in chron]
    streak, last = 0, ups[-1]
    for u in reversed(ups):
        if u == last:
            streak += 1
        else:
            break
    beats = [r for r in chron if r.get("surprise_pct") is not None]
    if o_avg and r_avg > o_avg * 1.15:
        vol = "up"
    elif o_avg and r_avg < o_avg * 0.85:
        vol = "down"
    else:
        vol = "flat"
    return {"recent_avg": round(r_avg, 2), "older_avg": None if o_avg is None else round(o_avg, 2), "vol": vol, "slope": None if sl is None else round(sl, 3),
            "ma3": ma3, "streak": streak, "streak_dir": "up" if last else "down",
            "up_rate": round(sum(ups) / len(ups) * 100), "beat_rate": round(sum(1 for r in beats if r["surprise_pct"] >= 0) / len(beats) * 100) if beats else None,
            "avg_surprise": round(statistics.mean(r["surprise_pct"] for r in beats), 1) if beats else None,
            "after_beat_avg": round(statistics.mean(r["day_pct"] for r in beats if r["surprise_pct"] >= 0), 2) if any(r["surprise_pct"] >= 0 for r in beats) else None,
            "after_miss_avg": round(statistics.mean(r["day_pct"] for r in beats if r["surprise_pct"] < 0), 2) if any(r["surprise_pct"] < 0 for r in beats) else None}


HIST_EDGES = [-1e9, -10, -5, -2, 0, 2, 5, 10, 1e9]
HIST_LABELS = ["< −10%", "−10 a −5", "−5 a −2", "−2 a 0", "0 a 2", "2 a 5", "5 a 10", "> 10%"]


def _hist(rows):
    out = [0] * 8
    for r in rows:
        for i in range(8):
            if HIST_EDGES[i] <= r["day_pct"] < HIST_EDGES[i + 1]:
                out[i] += 1
                break
    return {"labels": HIST_LABELS, "counts": out}


# ---------------------------------------------------------------- dividendos
def _history(sym, demo, price, amt=None):
    if demo:
        if not amt:
            return []
        base = amt
        today = date(2026, 10, 7)
        out = []
        for k in range(12):
            d = today - timedelta(days=int(91.3 * k) + 20)
            out.append({"ex": d.isoformat(), "amount": round(base / (1.03 ** (k / 4)), 3)})
        return out
    if not config.ALPHAVANTAGE_KEY:
        return None
    q = urllib.parse.urlencode({"function": "DIVIDENDS", "symbol": sym, "apikey": config.ALPHAVANTAGE_KEY})
    data = _cached(f"div:{sym}", 24 * 3600, lambda: _get_json("https://www.alphavantage.co/query?" + q))
    out = []
    for r in (data.get("data") or [])[:24]:
        try:
            out.append({"ex": r["ex_dividend_date"], "amount": float(r["amount"])})
        except (KeyError, ValueError, TypeError):
            continue
    return out


def dividends(sym, provider, price, history=True):
    demo = provider.name == "demo"
    f = _cached(f"fund:{sym}:{provider.name}", 6 * 3600, lambda: provider.fundamentals(sym) or {})
    y = f.get("div_yield")
    amt, freq = f.get("div_amount"), f.get("div_freq") or 4
    annual = (amt or 0) * freq if amt else (price * (y or 0) / 100)
    out = {"symbol": sym, "price": price, "yield": y, "amount": amt, "freq": freq, "annual": round(annual, 3), "income_100": round(annual * 100, 2),
           "next_date": f.get("div_date"), "pays": bool(annual), "history": None, "history_note": None, "growth": None}
    if history:
        h = _history(sym, demo, price, amt)
        if h is None:
            out["history_note"] = "Falta ALPHAVANTAGE_API_KEY para el historial de pagos (gratuita en alphavantage.co)."
        else:
            out["history"] = h
            if len(h) >= 5:
                a, b = h[0]["amount"], h[min(len(h) - 1, 4 * ((len(h) - 1) // 4))]["amount"]
                yrs = ((len(h) - 1) // 4) or 1
                if a and b:
                    out["growth"] = round(((a / b) ** (1 / yrs) - 1) * 100, 2)
    return out
