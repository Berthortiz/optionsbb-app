"""Cover call «de recubrimiento» (overlay) sobre una acción, con primas ESTIMADAS (Black-Scholes).

Contabilidad: P&L total = P&L de las acciones + P&L del call vendido.
  Cada ciclo (≈ 1 mes) se vende un call fuera del dinero (OTM %) y se cobra la prima.
  Al vencer: si el precio sube más que el strike, el call cuesta (precio − strike) por acción; si no, se queda la prima.
  Si te asignan, se asume que recompras las acciones al precio de vencimiento (así la posición sigue y el P&L de las acciones no cambia).
Solo se cubren lotes completos de 100 acciones. Las primas son un modelo (no cotizaciones reales): úsalo para comparar, no como promesa."""
import math

CYCLE = 21            # días de bolsa por ciclo (~30 días calendario)
DTE_YEARS = 30 / 365
RATE = 0.04
MIN_VOL, MAX_VOL = 0.15, 1.8


class OverlayError(ValueError):
    pass


def _cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bs_call(s, k, t, vol, r=RATE):
    if t <= 0 or vol <= 0:
        return max(0.0, s - k)
    d1 = (math.log(s / k) + (r + vol * vol / 2) * t) / (vol * math.sqrt(t))
    d2 = d1 - vol * math.sqrt(t)
    return s * _cdf(d1) - k * math.exp(-r * t) * _cdf(d2)


def realized_vol(closes):
    r = [math.log(b / a) for a, b in zip(closes, closes[1:]) if a > 0 and b > 0]
    if len(r) < 5:
        return None
    m = sum(r) / len(r)
    var = sum((x - m) ** 2 for x in r) / (len(r) - 1)
    return min(MAX_VOL, max(MIN_VOL, math.sqrt(var * 252)))


def run_cycles(prices, vols, otm, shares, years=None):
    """prices: [P0..Pn] (precio al inicio de cada ciclo y al final); vols: volatilidad anual por ciclo.
    Devuelve el detalle por ciclo y los totales."""
    if len(prices) < 2 or len(vols) != len(prices) - 1:
        raise OverlayError("Se necesitan al menos 2 precios")
    if any(p is None or p <= 0 for p in prices):
        raise OverlayError("Los precios deben ser positivos")
    if not (0 <= otm <= 0.5):
        raise OverlayError("El % fuera del dinero debe estar entre 0 y 50")
    if not (0 < shares <= 10_000_000):
        raise OverlayError("Número de acciones fuera de rango")
    lots = int(shares // 100)
    covered = lots * 100
    cycles, cum_prem, cum_over = [], 0.0, 0.0
    for i in range(len(prices) - 1):
        s0, s1, vol = prices[i], prices[i + 1], vols[i]
        k = s0 * (1 + otm)
        t = (years[i] if years else DTE_YEARS)
        prem = bs_call(s0, k, t, vol)
        owed = max(0.0, s1 - k)
        over = (prem - owed) * covered
        cum_prem += prem * covered
        cum_over += over
        cycles.append({"i": i + 1, "start": s0, "end": s1, "strike": k, "premium": prem, "premium_total": prem * covered,
                       "assigned": s1 > k, "overlay": over, "stock_pnl": (s1 - s0) * shares,
                       "cum_stock": (s1 - prices[0]) * shares, "cum_overlay": cum_over, "cum_total": (s1 - prices[0]) * shares + cum_over})
    stock = (prices[-1] - prices[0]) * shares
    cost = prices[0] * shares
    out = {"cycles": cycles, "lots": lots, "covered_shares": covered, "start": prices[0], "end": prices[-1],
           "stock_pnl": stock, "premiums": cum_prem, "overlay_pnl": cum_over, "total_pnl": stock + cum_over,
           "stock_pct": stock / cost * 100, "overlay_pct": cum_over / cost * 100, "total_pct": (stock + cum_over) / cost * 100,
           "assigned": sum(1 for c in cycles if c["assigned"]), "n": len(cycles),
           "absorbed_pct": (min(100.0, cum_over / -stock * 100) if stock < 0 and cum_over > 0 else None)}
    return out


def from_daily(closes, shares, otm=0.05, iv=None):
    """closes: cierres diarios del periodo (el primero = inicio). Ciclos de 21 días; el último parcial si quedan ≥5 días."""
    if len(closes) < 6:
        raise OverlayError("Historia insuficiente")
    idx = list(range(0, len(closes) - 1, CYCLE))
    bounds = [closes[i] for i in idx]
    ends = idx[1:] + [len(closes) - 1]
    prices = [closes[idx[0]]] + [closes[e] for e in ends]
    vols, years = [], []
    for i, e in zip(idx, ends):
        n = e - i
        if n < 5 and len(idx) > 1 and e == len(closes) - 1 and i != idx[0]:
            # resto demasiado corto: se fusiona con el ciclo anterior
            pass
        look = closes[max(0, i - 60):i + 1]
        v = iv if iv else (realized_vol(look) or realized_vol(closes) or 0.35)
        vols.append(v)
        years.append(max(n, 1) / 252)
    if len(prices) > 2 and ends[-1] - idx[-1] < 5:   # fusiona ciclo final corto
        prices.pop(-2); vols.pop(); years.pop()
        years[-1] = (len(closes) - 1 - idx[-2]) / 252
    r = run_cycles(prices, vols, otm, shares, years)
    r["vol"] = sum(vols) / len(vols)
    return r


def classify(stock_pct, flat=5.0):
    if abs(stock_pct) < flat:
        return "flat"
    return "up" if stock_pct > 0 else "down"
