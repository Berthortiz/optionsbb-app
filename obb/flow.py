"""Volumen del día D  ->  open interest de la mañana D+1.

El OI lo publica la OCC cada noche, así que:
    CLOSE   (D, ~16:15 ET): volumen de D y OI0 (el OI de esa mañana, que aún no incluye D)
    MORNING (D+1, ~9:00 ET): OI1 (ya incluye lo negociado en D)
    ΔOI = OI1 - OI0 ;  %OI = ΔOI / OI0 ;  conversión = ΔOI / volumen(D)
"""
from . import db

CONTRACTS_PER_SYMBOL = 40
MIN_VOL_SAVE = 10
INSERT = ("INSERT OR REPLACE INTO contract_snaps(snap_date,kind,occ,underlying,cp,strike,expiry,volume,oi,last)"
          " VALUES(?,?,?,?,?,?,?,?,?,?)")


def save_close(snap_date: str, chains: dict) -> int:
    rows = []
    for sym, cs in chains.items():
        top = sorted(cs, key=lambda c: c["volume"], reverse=True)[:CONTRACTS_PER_SYMBOL]
        for c in top:
            if c["volume"] >= MIN_VOL_SAVE:
                rows.append((snap_date, "CLOSE", c["occ"], sym, c["cp"], c["strike"], c["expiry"], c["volume"], c["oi"], c.get("last")))
    db.many(INSERT, rows)
    return len(rows)


def save_morning(snap_date: str, chains: dict) -> int:
    prev = db.q1("SELECT max(snap_date) d FROM contract_snaps WHERE kind='CLOSE' AND snap_date<?", (snap_date,))
    if not prev or not prev["d"]:
        return 0
    wanted = {r["occ"] for r in db.q("SELECT occ FROM contract_snaps WHERE kind='CLOSE' AND snap_date=?", (prev["d"],))}
    rows = []
    for sym, cs in chains.items():
        for c in cs:
            if c["occ"] in wanted:
                rows.append((snap_date, "MORNING", c["occ"], sym, c["cp"], c["strike"], c["expiry"], 0, c["oi"], c.get("last")))
    db.many(INSERT, rows)
    return len(rows)


def has_snapshot(kind: str, snap_date: str) -> bool:
    return db.q1("SELECT 1 FROM contract_snaps WHERE kind=? AND snap_date=? LIMIT 1", (kind, snap_date)) is not None


def available_pairs():
    """Pares (cierre D, mañana D+1) con datos completos, del más reciente al más antiguo."""
    closes = [r["d"] for r in db.q("SELECT DISTINCT snap_date d FROM contract_snaps WHERE kind='CLOSE' ORDER BY d")]
    mornings = [r["d"] for r in db.q("SELECT DISTINCT snap_date d FROM contract_snaps WHERE kind='MORNING' ORDER BY d")]
    pairs = []
    for i, d in enumerate(closes):
        nxt_close = closes[i + 1] if i + 1 < len(closes) else "9999-12-31"
        m = next((x for x in mornings if x > d and x <= nxt_close), None)
        if m:
            pairs.append({"close_date": d, "morning_date": m})
    return list(reversed(pairs))


LABEL_OPEN, LABEL_CLOSE, LABEL_MIX, LABEL_EXP = "Apertura probable", "Cierre probable", "Mixto", "Vencido"


def classify(conv, expired):
    if expired:
        return LABEL_EXP
    if conv is None:
        return LABEL_MIX
    if conv >= 0.5:
        return LABEL_OPEN
    if conv <= -0.5:
        return LABEL_CLOSE
    return LABEL_MIX


def compute(close_date: str, morning_date: str) -> dict:
    rows = db.q(
        """SELECT c.occ, c.underlying u, c.cp, c.strike, c.expiry, c.volume, c.oi oi0, c.last, m.oi oi1
           FROM contract_snaps c
           LEFT JOIN contract_snaps m ON m.occ=c.occ AND m.kind='MORNING' AND m.snap_date=?
           WHERE c.kind='CLOSE' AND c.snap_date=?""",
        (morning_date, close_date),
    )
    contracts = []
    for r in rows:
        vol, oi0, oi1 = r["volume"], r["oi0"], r["oi1"]
        expired = oi1 is None and r["expiry"] <= close_date
        if oi1 is None and not expired:
            continue  # sin dato de OI al día siguiente: no se puede evaluar
        d_oi = None if oi1 is None else oi1 - oi0
        pct = (d_oi / oi0 * 100) if (d_oi is not None and oi0 > 0) else None
        conv = (d_oi / vol) if (d_oi is not None and vol > 0) else None
        contracts.append({
            "occ": r["occ"], "symbol": r["u"], "cp": r["cp"], "strike": r["strike"], "expiry": r["expiry"],
            "volume": vol, "oi0": oi0, "oi1": oi1, "d_oi": d_oi, "pct": pct, "conv": conv,
            "vol_oi": (vol / oi0) if oi0 > 0 else None, "label": classify(conv, expired), "last": r["last"],
        })
    contracts.sort(key=lambda c: c["volume"], reverse=True)

    stocks = {}
    for c in contracts:
        if c["label"] == LABEL_EXP:
            continue
        s = stocks.setdefault(c["symbol"], {"symbol": c["symbol"], "call_vol": 0, "put_vol": 0, "call_d_oi": 0, "put_d_oi": 0,
                                            "oi0": 0, "top": None})
        k = "call" if c["cp"] == "C" else "put"
        s[k + "_vol"] += c["volume"]
        s[k + "_d_oi"] += c["d_oi"]
        s["oi0"] += c["oi0"]
        if s["top"] is None or c["volume"] > s["top"]["volume"]:
            s["top"] = c
    by_stock = []
    for s in stocks.values():
        tot_d = s["call_d_oi"] + s["put_d_oi"]
        s["total_vol"] = s["call_vol"] + s["put_vol"]
        s["pcr"] = (s["put_vol"] / s["call_vol"]) if s["call_vol"] else None
        s["pct"] = (tot_d / s["oi0"] * 100) if s["oi0"] else None
        s["d_oi"] = tot_d
        by_stock.append(s)
    by_stock.sort(key=lambda s: s["total_vol"], reverse=True)

    live = [c for c in contracts if c["label"] != LABEL_EXP]
    summary = {
        "contracts": len(live),
        "volume": sum(c["volume"] for c in live),
        "d_oi": sum(c["d_oi"] for c in live),
        "opening": sum(1 for c in live if c["label"] == LABEL_OPEN),
        "closing": sum(1 for c in live if c["label"] == LABEL_CLOSE),
        "mixed": sum(1 for c in live if c["label"] == LABEL_MIX),
        "expired": len(contracts) - len(live),
    }
    oi0_tot = sum(c["oi0"] for c in live)
    summary["pct"] = (summary["d_oi"] / oi0_tot * 100) if oi0_tot else None
    return {"close_date": close_date, "morning_date": morning_date, "summary": summary,
            "contracts": contracts, "by_stock": by_stock}


# ---------- vista en vivo (Centro de Comando) ----------
def top_live(chains: dict, n=8):
    allc = [c for cs in chains.values() for c in cs]
    allc.sort(key=lambda c: c["volume"], reverse=True)
    return [{"symbol": c["underlying"], "cp": c["cp"], "strike": c["strike"], "expiry": c["expiry"], "volume": c["volume"],
             "oi": c["oi"], "vol_oi": (c["volume"] / c["oi"]) if c["oi"] else None, "last": c["last"]} for c in allc[:n]]


def volume_by_stock(chains: dict):
    out = {}
    for sym, cs in chains.items():
        cv = sum(c["volume"] for c in cs if c["cp"] == "C")
        pv = sum(c["volume"] for c in cs if c["cp"] == "P")
        out[sym] = {"call_vol": cv, "put_vol": pv, "total": cv + pv, "pcr": (pv / cv) if cv else None}
    return out


def idea_of_the_day(vbs: dict, quotes: dict) -> str:
    ranked = sorted(vbs.items(), key=lambda kv: kv[1]["total"], reverse=True)[:2]
    if not ranked or ranked[0][1]["total"] == 0:
        return ""

    def trend(sym):
        v, q = vbs[sym], quotes.get(sym) or {}
        ch = q.get("change_pct") or 0
        if ch > 0 and v["call_vol"] >= v["put_vol"]:
            return "alcista"
        if ch < 0 and v["put_vol"] >= v["call_vol"]:
            return "bajista"
        return "mixta"

    names = [s for s, _ in ranked]
    ts = [trend(s) for s in names]
    if len(names) == 1:
        return f"Mayor volumen en opciones: {names[0]} (tendencia {ts[0]})."
    if ts[0] == ts[1]:
        return f"Mayor volumen en {names[0]} y {names[1]} con tendencia {ts[0]}."
    return f"Mayor volumen en {names[0]} (tendencia {ts[0]}) y {names[1]} (tendencia {ts[1]})."
