"""Cover call: análisis de una cadena, calculadora de una operación y simulador mensual con recompra ("rueda").

Convenciones:
  · 1 contrato = 100 acciones; prima y strikes son por acción.
  · Ejercicio al vencimiento: la opción se ejerce si precio_al_vencimiento > strike (ITM).
    (El ejercicio anticipado es posible, sobre todo cerca de dividendos; aquí se evalúa solo al vencimiento.)
  · Ganancia máxima = (strike − costo + prima) × acciones − comisiones, solo si te ejercen.
  · Punto de equilibrio = costo − prima.
"""
import math
import re
from datetime import date, datetime

MAX_CYCLES = 36
MAX_CHAIN = 400


class CCError(ValueError):
    pass


def num(v, name, *, minv=None, maxv=None, positive=False, default=None):
    if v is None or v == "":
        if default is not None:
            return default
        raise CCError(f"Falta {name}")
    try:
        x = float(str(v).replace("$", "").replace(",", "").strip())
    except (TypeError, ValueError):
        raise CCError(f"{name} no es un número")
    if not math.isfinite(x):
        raise CCError(f"{name} no es válido")
    if positive and x <= 0:
        raise CCError(f"{name} debe ser mayor que 0")
    if minv is not None and x < minv:
        raise CCError(f"{name} no puede ser menor que {minv}")
    if maxv is not None and x > maxv:
        raise CCError(f"{name} no puede ser mayor que {maxv}")
    return x


def parse_date(s, name):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except ValueError:
        raise CCError(f"{name} debe tener formato AAAA-MM-DD")


# ---------------------------------------------------------------- cadena pegada
HEAD = {
    "strike": "strike", "bid": "bid", "ask": "ask", "delta": "delta", "volume": "volume", "vol": "volume",
    "oi": "oi", "open.int": "oi", "openint": "oi", "open_interest": "oi", "interes": "oi",
}
DEFAULT_ORDER = ["strike", "bid", "ask", "delta", "volume", "oi"]


def _tok_num(t):
    t = t.strip().replace("$", "")
    if t.upper() in ("N/A", "NAN", "-", "--", ""):
        return None
    try:
        return float(t.replace(",", ""))
    except ValueError:
        return "x"


def parse_chain_text(text: str):
    """Texto pegado → ([{strike,bid,ask,delta,volume,oi}], [avisos]). Columnas: strike bid ask [delta] [volumen] [OI]."""
    rows, warns, order = [], [], list(DEFAULT_ORDER)
    lines = [l.strip() for l in (text or "").replace("\r", "").split("\n") if l.strip()]
    if len(lines) > MAX_CHAIN + 1:
        raise CCError(f"Máximo {MAX_CHAIN} filas")
    for n, line in enumerate(lines, 1):
        if "\t" in line or ";" in line:
            toks = re.split(r"[\t;]+", line)
        elif " " not in line and "," in line:
            toks = line.split(",")
        else:
            toks = line.split()
        toks = [t for t in toks if not re.fullmatch(r"[A-Za-z]", t.strip())]  # letras de bolsa de TOS (A, W, Q…)
        low = [t.strip().lower() for t in toks]
        if any(t in HEAD for t in low):
            order = [HEAD.get(t) for t in low]
            continue
        vals = [_tok_num(t) for t in toks]
        if "x" in vals:
            warns.append(f"Fila {n} ignorada (texto no numérico): {line[:40]}")
            continue
        r = {k: None for k in DEFAULT_ORDER}
        for k, v in zip(order, vals):
            if k:
                r[k] = v
        if r["strike"] is None or r["strike"] <= 0 or (r["bid"] is None and r["ask"] is None):
            warns.append(f"Fila {n} ignorada (falta strike o bid/ask): {line[:40]}")
            continue
        r["bid"] = r["bid"] if r["bid"] is not None else 0.0
        r["ask"] = r["ask"] if r["ask"] is not None else r["bid"]
        if r["ask"] < r["bid"]:
            warns.append(f"Strike {r['strike']:g}: el ask es menor que el bid (se invirtieron)")
            r["bid"], r["ask"] = r["ask"], r["bid"]
        rows.append(r)
    rows.sort(key=lambda r: r["strike"])
    seen, out = set(), []
    for r in rows:
        if r["strike"] in seen:
            warns.append(f"Strike {r['strike']:g} repetido: se usó la primera fila")
            continue
        seen.add(r["strike"])
        out.append(r)
    return out, warns


def clean_chain(chain):
    """Valida una cadena ya estructurada (lista de dicts)."""
    if not isinstance(chain, list) or not chain:
        raise CCError("La cadena está vacía")
    if len(chain) > MAX_CHAIN:
        raise CCError(f"Máximo {MAX_CHAIN} filas")
    out = []
    for r in chain:
        if not isinstance(r, dict):
            raise CCError("Cadena no válida")
        k = num(r.get("strike"), "strike", positive=True)
        bid = num(r.get("bid"), "bid", minv=0, default=0.0)
        ask = num(r.get("ask"), "ask", minv=0, default=bid)
        d = {"strike": k, "bid": min(bid, ask), "ask": max(bid, ask)}
        for f in ("delta", "volume", "oi"):
            try:
                d[f] = None if r.get(f) in (None, "") else float(r[f])
            except (TypeError, ValueError):
                d[f] = None
        out.append(d)
    out.sort(key=lambda r: r["strike"])
    return out


# ---------------------------------------------------------------- una operación
def premium_of(row, basis):
    if basis == "mid":
        return round((row["bid"] + row["ask"]) / 2, 4)
    return row["bid"]


def trade_metrics(*, spot, cost, strike, premium, shares, dte, commission_per_contract=0.0):
    """Todas las cifras de vender un call cubierto. `commission_per_contract` se cobra al vender (una vez)."""
    contracts = max(1, int(shares // 100))
    comm = commission_per_contract * contracts
    invested = cost * shares
    gain_if_called = (strike - cost + premium) * shares - comm
    keep_flat = premium * shares - comm            # acción sin cambios al vencimiento
    out = {
        "strike": strike, "premium": premium, "credit": round(premium * shares - comm, 2),
        "assign_above": strike,                       # precio al que debe LLEGAR (superar) para que te ejerzan
        "distance_pct": (strike / spot - 1) * 100,    # cuánto debe subir desde el precio actual
        "breakeven": round(cost - premium, 4),
        "downside_protection_pct": premium / spot * 100,
        "max_profit": round(gain_if_called, 2),
        "max_profit_pct": gain_if_called / invested * 100 if invested else None,
        "stock_gain_to_strike": round((strike - cost) * shares, 2),
        "flat_profit": round(keep_flat, 2),
        "flat_profit_pct": keep_flat / invested * 100 if invested else None,
        "premium_yield_pct": premium / spot * 100,
        "locks_loss": gain_if_called < 0,
        "commission": round(comm, 2),
    }
    if dte and dte > 0:
        out["annualized_if_called_pct"] = out["max_profit_pct"] * 365 / dte
        out["annualized_flat_pct"] = out["flat_profit_pct"] * 365 / dte
    out["dte"] = dte
    return out


def payoff(*, spot, cost, strike, premium, shares, commission_per_contract=0.0, points=25):
    comm = commission_per_contract * max(1, int(shares // 100))
    be = cost - premium
    xs = {round(spot * (0.75 + 0.5 * i / (points - 1)), 2) for i in range(points)} | {round(strike, 2), round(be, 2), round(spot, 2)}
    rows = []
    for s in sorted(x for x in xs if x > 0):
        pl = (min(s, strike) - cost + premium) * shares - comm
        rows.append({"price": s, "pl": round(pl, 2), "pl_pct": pl / (cost * shares) * 100, "assigned": s > strike})
    return rows


def pick_strike(chain, spot, k):
    """k-ésimo strike por encima del precio (k=1 → el strike inmediatamente superior). Devuelve índice en `chain` o None."""
    above = [i for i, r in enumerate(chain) if r["strike"] > spot]
    if not above:
        return None
    return above[min(k - 1, len(above) - 1)], (k - 1) >= len(above)  # (índice, se_quedó_corto)


def analyze(data: dict) -> dict:
    """Entrada: spot, cost (costo por acción; por defecto = spot), shares, dte o (sell_date, expiry), basis, commission, k,
    y UNA de: chain (lista o texto)  |  strike+premium manuales."""
    spot = num(data.get("spot"), "Precio de la acción", positive=True)
    cost = num(data.get("cost"), "Costo por acción", positive=True, default=spot)
    shares = int(num(data.get("shares"), "Acciones", minv=100, maxv=1_000_000, default=100))
    if shares % 100:
        raise CCError("Las acciones deben ser múltiplos de 100 (1 contrato = 100 acciones)")
    basis = data.get("basis", "bid")
    if basis not in ("bid", "mid"):
        raise CCError("La base de la prima debe ser bid o mid")
    comm = num(data.get("commission"), "Comisión por contrato", minv=0, maxv=100, default=0.0)
    k = int(num(data.get("k"), "Strike por encima (k)", minv=1, maxv=50, default=5))
    dte = None
    if data.get("expiry") and data.get("sell_date"):
        dte = (parse_date(data["expiry"], "Vencimiento") - parse_date(data["sell_date"], "Fecha de venta")).days
        if dte <= 0:
            raise CCError("El vencimiento debe ser posterior a la fecha de venta")
    elif data.get("dte") not in (None, ""):
        dte = int(num(data["dte"], "Días al vencimiento", minv=1, maxv=1000))
    warns, chain, rows = [], None, []
    if data.get("chain_text"):
        chain, warns = parse_chain_text(data["chain_text"])
    elif data.get("chain"):
        chain = clean_chain(data["chain"])
    if data.get("chain_text") and not chain:
        raise CCError("No pude leer ninguna fila de la cadena")
    if chain:
        for r in chain:
            p = premium_of(r, basis)
            m = trade_metrics(spot=spot, cost=cost, strike=r["strike"], premium=p, shares=shares, dte=dte, commission_per_contract=comm)
            spread = (r["ask"] - r["bid"]) / r["ask"] if r["ask"] else None
            ordinal = None
            if r["strike"] > spot:
                ordinal = 1 + sum(1 for x in chain if spot < x["strike"] < r["strike"])
            rows.append({**m, "delta": r.get("delta"), "volume": r.get("volume"), "oi": r.get("oi"), "bid": r["bid"], "ask": r["ask"],
                         "spread_pct": spread * 100 if spread is not None else None, "ordinal_above": ordinal,
                         "itm": r["strike"] <= spot,
                         "liquid": bool(spread is not None and spread <= 0.10 and (r.get("oi") or 0) >= 100)})
        pk = pick_strike(chain, spot, k)
        if pk is None:
            raise CCError("La cadena no tiene strikes por encima del precio actual")
        idx, short = pk
        if short:
            warns.append(f"La cadena solo tiene {sum(1 for r in chain if r['strike'] > spot)} strikes sobre el precio; se usó el último.")
        chosen = rows[idx]
        if data.get("strike") not in (None, ""):
            want = num(data["strike"], "Strike")
            ch = next((r for r in rows if abs(r["strike"] - want) < 1e-9), None)
            if not ch:
                raise CCError(f"El strike {want:g} no está en la cadena")
            chosen = ch
        for r in rows:
            r["recommended"] = r is chosen
    else:
        strike = num(data.get("strike"), "Strike", positive=True)
        premium = num(data.get("premium"), "Prima", minv=0)
        chosen = trade_metrics(spot=spot, cost=cost, strike=strike, premium=premium, shares=shares, dte=dte, commission_per_contract=comm)
        chosen["ordinal_above"] = None
    if chosen["premium"] <= 0:
        warns.append("La prima del strike elegido es 0 (¿bid vacío?). Revisa los datos o usa la base 'mid'.")
    if chosen["strike"] <= spot:
        warns.append("El strike elegido está dentro del dinero (ITM): casi seguro te ejercen.")
    if chosen["locks_loss"]:
        warns.append("Con ese strike, si te ejercen pierdes dinero respecto a tu costo.")
    if cost > spot * 1.0 and chosen["strike"] < cost:
        warns.append("El strike está por debajo de tu costo por acción.")
    pay = payoff(spot=spot, cost=cost, strike=chosen["strike"], premium=chosen["premium"], shares=shares, commission_per_contract=comm)
    return {"inputs": {"spot": spot, "cost": cost, "shares": shares, "basis": basis, "commission": comm, "k": k, "dte": dte},
            "chain": rows, "chosen": chosen, "payoff": pay, "warnings": warns}


# ---------------------------------------------------------------- simulador mensual (rueda)
def simulate_wheel(params: dict, cycles: list) -> dict:
    shares = int(num(params.get("shares"), "Acciones", minv=100, maxv=1_000_000, default=100))
    if shares % 100:
        raise CCError("Las acciones deben ser múltiplos de 100")
    contracts = shares // 100
    k = int(num(params.get("k"), "Strike por encima (k)", minv=1, maxv=50, default=5))
    basis = params.get("basis", "bid")
    if basis not in ("bid", "mid"):
        raise CCError("La base de la prima debe ser bid o mid")
    comm = num(params.get("commission"), "Comisión por contrato", minv=0, maxv=100, default=0.0)
    rebuy = bool(params.get("rebuy", True))
    if not isinstance(cycles, list) or not cycles:
        raise CCError("Agrega al menos un mes")
    if len(cycles) > MAX_CYCLES:
        raise CCError(f"Máximo {MAX_CYCLES} meses")

    cy = []
    for i, c in enumerate(cycles, 1):
        sd, ex = parse_date(c.get("sell_date"), f"Mes {i}: fecha de venta"), parse_date(c.get("expiry"), f"Mes {i}: vencimiento")
        if ex <= sd:
            raise CCError(f"Mes {i}: el vencimiento debe ser posterior a la venta")
        if cy and sd < cy[-1]["sd"]:
            raise CCError(f"Mes {i}: las fechas deben ir en orden")
        spot = num(c.get("spot"), f"Mes {i}: precio de la acción", positive=True)
        chain = clean_chain(c["chain"]) if c.get("chain") else (parse_chain_text(c["chain_text"])[0] if c.get("chain_text") else None)
        if not chain:
            raise CCError(f"Mes {i}: falta la cadena de opciones (strikes con bid/ask)")
        se = c.get("spot_at_expiry")
        ck = c.get("k")
        ck = k if ck in (None, "") else int(num(ck, f"Mes {i}: strike por encima", minv=1, maxv=50))
        want = c.get("strike")
        want = None if want in (None, "") else num(want, f"Mes {i}: strike", positive=True)
        cy.append({"sd": sd, "ex": ex, "spot": spot, "chain": chain, "k": ck, "want": want,
                   "se": None if se in (None, "") else num(se, f"Mes {i}: precio al vencimiento", positive=True)})

    init_price = num(params.get("initial_cost"), "Costo inicial", positive=True, default=cy[0]["spot"])
    initial_invested = init_price * shares
    cash, held, cost = -initial_invested, shares, init_price
    prev_eq = 0.0
    rows, warns, peak, mdd = [], [], 0.0, 0.0
    total_premium = assigned_n = closed_n = 0
    last_price = init_price
    stopped = None
    for n, c in enumerate(cy, 1):
        rebought = False
        if held == 0:
            if not rebuy:
                stopped = f"Mes {n}: te ejercieron y la recompra está desactivada; la simulación termina en efectivo."
                break
            cash -= c["spot"] * shares
            held, cost, rebought = shares, c["spot"], True
        if c["want"] is not None:
            idx = next((j for j, x in enumerate(c["chain"]) if abs(x["strike"] - c["want"]) < 1e-9), None)
            if idx is None:
                raise CCError(f"Mes {n}: el strike {c['want']:g} no está en la cadena")
            if c["chain"][idx]["strike"] <= c["spot"]:
                warns.append(f"Mes {n}: el strike {c['want']:g} está dentro del dinero (ITM).")
            short = False
        else:
            pk = pick_strike(c["chain"], c["spot"], c["k"])
            if pk is None:
                raise CCError(f"Mes {n}: la cadena no tiene strikes por encima de {c['spot']:g}")
            idx, short = pk
        if short:
            warns.append(f"Mes {n}: la cadena tiene pocos strikes sobre el precio; se usó el último.")
        r = c["chain"][idx]
        prem = premium_of(r, basis)
        if prem <= 0:
            warns.append(f"Mes {n}: la prima del strike {r['strike']:g} es 0.")
        credit = prem * shares - comm * contracts
        cash += credit
        total_premium += credit
        ordinal = 1 + sum(1 for x in c["chain"] if c["spot"] < x["strike"] < r["strike"])
        row = {"n": n, "sell_date": c["sd"].isoformat(), "expiry": c["ex"].isoformat(), "dte": (c["ex"] - c["sd"]).days,
               "spot": c["spot"], "rebought": rebought, "cost": round(cost, 4), "strike": r["strike"], "ordinal_above": ordinal,
               "bid": r["bid"], "ask": r["ask"], "premium": prem, "credit": round(credit, 2), "delta": r.get("delta"),
               "premium_pct": prem / c["spot"] * 100, "spot_at_expiry": c["se"]}
        if c["se"] is None:
            row.update(status="abierta", equity=round(cash + held * c["spot"], 2))
            row["cycle_pl"] = round(row["equity"] - prev_eq, 2)
            rows.append(row)
            stopped = f"Mes {n}: aún sin precio al vencimiento; la posición queda abierta."
            last_price = c["spot"]
            break
        s = c["se"]
        closed_n += 1
        last_price = s
        if s > r["strike"]:
            cash += r["strike"] * shares
            held = 0
            assigned_n += 1
            row.update(status="ejercida", stock_pl=round((r["strike"] - cost) * shares, 2), missed_upside=round((s - r["strike"]) * shares, 2))
        else:
            row.update(status="no ejercida", stock_pl=round((s - cost) * shares, 2), missed_upside=0.0)
        eq = cash + held * s
        row["equity"] = round(eq, 2)
        row["cycle_pl"] = round(eq - prev_eq, 2)
        prev_eq = eq
        peak = max(peak, eq)
        mdd = max(mdd, peak - eq)
        rows.append(row)
        nxt = cy[n] if n < len(cy) else None
        if held == 0 and nxt:
            row["rebuy_next"] = nxt["spot"]
            row["rebuy_gap"] = round((nxt["spot"] - r["strike"]) * shares, 2)  # >0: recompras más caro que tu precio de venta

    if not rows:
        raise CCError(stopped or "No hay meses que simular")
    final_eq = rows[-1]["equity"]
    first_sd, last_dt = cy[0]["sd"], cy[len(rows) - 1]["ex"] if rows[-1]["status"] != "abierta" else cy[len(rows) - 1]["sd"]
    days = max(1, (last_dt - first_sd).days)
    bh = (last_price - init_price) * shares
    summary = {
        "months": len(rows), "closed": closed_n, "assigned": assigned_n,
        "assigned_pct": assigned_n / closed_n * 100 if closed_n else None,
        "total_premium": round(total_premium, 2), "total_pl": final_eq,
        "return_pct": final_eq / initial_invested * 100, "annualized_pct": final_eq / initial_invested * 100 * 365 / days,
        "invested": round(initial_invested, 2), "days": days, "buy_hold_pl": round(bh, 2),
        "buy_hold_pct": bh / initial_invested * 100, "vs_buy_hold": round(final_eq - bh, 2),
        "max_drawdown": round(mdd, 2), "last_price": last_price,
        "missed_upside": round(sum(r.get("missed_upside", 0) for r in rows), 2),
        "open": rows[-1]["status"] == "abierta",
        "ended_in_cash": rows[-1]["status"] == "ejercida" and (len(rows) == len(cy) or stopped is not None),
    }
    return {"rows": rows, "summary": summary, "warnings": warns + ([stopped] if stopped else []),
            "equity": [{"n": r["n"], "date": r["expiry"] if r["status"] != "abierta" else r["sell_date"], "pl": r["equity"]} for r in rows]}
