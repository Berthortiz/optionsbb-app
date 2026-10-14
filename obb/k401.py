"""Calculadoras de retiro / 401(k): proyección de 3 escenarios, meta de retiro y efecto de comisiones.

Todo son SUPUESTOS editables, no promesas de rendimiento. Capitalización mensual.
"""
LIMITS_2026 = {"employee_401k": 24500, "ira": 7500, "year": 2026, "source": "IRS (anuncio de noviembre de 2025)"}
MAX_YEARS = 60


class KError(ValueError):
    pass


def _n(d, key, label, lo, hi, default=None):
    v = d.get(key)
    if v in (None, ""):
        if default is None:
            raise KError(f"Falta {label}")
        return default
    try:
        x = float(str(v).replace("$", "").replace(",", "").replace("%", ""))
    except ValueError:
        raise KError(f"{label} no es un número")
    if x != x or x in (float("inf"), float("-inf")):
        raise KError(f"{label} no es válido")
    if not lo <= x <= hi:
        raise KError(f"{label} debe estar entre {lo:g} y {hi:g}")
    return x


def _grow(balance, monthly, annual_rate, years):
    """Saldo al final de cada año: [(año, saldo)]."""
    r = (1 + annual_rate / 100) ** (1 / 12) - 1
    out, b = [], balance
    for y in range(1, int(years) + 1):
        for _ in range(12):
            b = b * (1 + r) + monthly
        out.append(b)
    return out


def employer_monthly(d, monthly):
    salary = _n(d, "salary", "Salario anual", 0, 10_000_000, 0)
    if salary > 0:
        rate = _n(d, "match_rate", "% que aporta la empresa", 0, 200, 0)
        cap = _n(d, "match_cap", "Tope del aporte (% del salario)", 0, 100, 0)
        return min(monthly, salary / 12 * cap / 100) * rate / 100
    return _n(d, "employer_monthly", "Aporte mensual de la empresa", 0, 100_000, 0)


def project(d: dict) -> dict:
    bal = _n(d, "balance", "Saldo actual", 0, 1e9, 0)
    monthly = _n(d, "monthly", "Aporte mensual", 0, 100_000, 0)
    years = int(_n(d, "years", "Años", 1, MAX_YEARS))
    infl = _n(d, "inflation", "Inflación", -5, 30, 3)
    cash = _n(d, "cash_rate", "Interés del efectivo", -5, 30, 0.5)
    stock = _n(d, "stock_return", "Rendimiento esperado de las acciones", -20, 40, 7)
    fee = _n(d, "fee", "Comisión anual", 0, 5, 0.1)
    prem = _n(d, "cc_premium_month", "Prima mensual del cover call (%)", 0, 10, 0.6)
    giveup = _n(d, "cc_giveup", "Subida que cedes al año (puntos %)", 0, 40, 6)
    share = _n(d, "cc_share", "% de la cartera con cover call", 0, 100, 100)
    emp = employer_monthly(d, monthly)
    contrib = monthly + emp
    cc_net = stock - giveup + prem * 12
    cc_rate = (share / 100) * cc_net + (1 - share / 100) * stock - fee
    scen = {
        "cash": {"label": "Efectivo (sin invertir)", "rate": cash},
        "stocks": {"label": "Acciones", "rate": stock - fee},
        "cc": {"label": "Acciones + Cover Call", "rate": cc_rate},
    }
    rows = []
    for k, s in scen.items():
        nominal = _grow(bal, contrib, s["rate"], years)
        s["nominal"] = nominal
        s["real"] = [v / (1 + infl / 100) ** (i + 1) for i, v in enumerate(nominal)]
        s["final"], s["final_real"] = nominal[-1], s["real"][-1]
    put = bal + contrib * 12 * years
    for y in range(years):
        rows.append({"year": y + 1, **{k: round(scen[k]["nominal"][y], 2) for k in scen}, **{k + "_real": round(scen[k]["real"][y], 2) for k in scen}})
    annual = monthly * 12
    warns = []
    if annual > LIMITS_2026["employee_401k"]:
        warns.append(f"Tu aporte anual (${annual:,.0f}) supera el límite 2026 de empleado para un 401(k) (${LIMITS_2026['employee_401k']:,}); los límites cambian cada año.")
    if prem * 12 - giveup <= 0 and share > 0:
        warns.append("Con estos supuestos el cover call no suma rendimiento: la prima no compensa la subida que cedes.")
    return {
        "inputs": {"balance": bal, "monthly": monthly, "employer_monthly": round(emp, 2), "years": years, "inflation": infl, "fee": fee},
        "contributed": round(put, 2), "rows": rows, "cc_net_return": round(cc_net, 2),
        "scenarios": {k: {"label": s["label"], "rate": round(s["rate"], 3), "final": round(s["final"], 2), "final_real": round(s["final_real"], 2)} for k, s in scen.items()},
        "cash_power_lost": round(1 - 1 / (1 + infl / 100) ** years, 4),
        "cash_real_vs_contrib": round(scen["cash"]["final_real"] - put, 2),
        "warnings": warns, "limits": LIMITS_2026,
    }


def _needed_monthly(target, bal, rate, years):
    r = (1 + rate / 100) ** (1 / 12) - 1
    n = years * 12
    grown = bal * (1 + r) ** n
    if target <= grown:
        return 0.0
    f = ((1 + r) ** n - 1) / r if r else n
    return (target - grown) / f


def goal(d: dict) -> dict:
    income = _n(d, "income", "Ingreso mensual deseado (en dólares de hoy)", 100, 1_000_000)
    years = int(_n(d, "years", "Años para retirarte", 1, MAX_YEARS))
    bal = _n(d, "balance", "Saldo actual", 0, 1e9, 0)
    infl = _n(d, "inflation", "Inflación", -5, 30, 3)
    wr = _n(d, "withdraw_rate", "Retiro anual sostenible (%)", 1, 10, 4)
    stock = _n(d, "stock_return", "Rendimiento esperado de las acciones", -20, 40, 7)
    cash = _n(d, "cash_rate", "Interés del efectivo", -5, 30, 0.5)
    fee = _n(d, "fee", "Comisión anual", 0, 5, 0.1)
    need_today = income * 12 / (wr / 100)
    need_future = need_today * (1 + infl / 100) ** years
    out = {}
    for k, label, rate in (("cash", "Efectivo", cash), ("stocks", "Acciones", stock - fee)):
        m = _needed_monthly(need_future, bal, rate, years)
        out[k] = {"label": label, "rate": round(rate, 3), "monthly": round(m, 2)}
    return {"need_today": round(need_today, 2), "need_future": round(need_future, 2), "years": years, "scenarios": out,
            "note": f"Con retiro de {wr:g} % anual, para ${income:,.0f}/mes de hoy necesitas ≈ ${need_today:,.0f} en dólares de hoy."}


def fees(d: dict) -> dict:
    bal = _n(d, "balance", "Saldo actual", 0, 1e9, 0)
    monthly = _n(d, "monthly", "Aporte mensual", 0, 100_000, 0)
    years = int(_n(d, "years", "Años", 1, MAX_YEARS))
    ret = _n(d, "stock_return", "Rendimiento bruto", -20, 40, 7)
    lo = _n(d, "fee_low", "Comisión baja", 0, 5, 0.1)
    hi = _n(d, "fee_high", "Comisión alta", 0, 5, 1.0)
    a = _grow(bal, monthly, ret - lo, years)[-1]
    b = _grow(bal, monthly, ret - hi, years)[-1]
    return {"low": {"fee": lo, "final": round(a, 2)}, "high": {"fee": hi, "final": round(b, 2)}, "lost": round(a - b, 2),
            "lost_pct": round((a - b) / a * 100, 2) if a else None}
