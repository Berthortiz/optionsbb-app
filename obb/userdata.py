"""Datos propios de cada usuario: preferencias, lista de seguimiento, estrategias seguidas y posiciones (401k)."""
import json
import re
import time

from . import analytics, db, library, plans

SYM_RE = re.compile(r"^[A-Z][A-Z.\-]{0,5}$")
MAX_WATCH = 30
MAX_HOLD = 30
PREF_KEYS = {"watch_periods", "profile", "k401", "lists", "whatif_cases"}
MAX_LIST = 10
MAX_ETFS = 5
MAX_ETF_POS = 20
PROFILES = {
    "conservador": {"name": "Conservador", "desc": "Prioriza proteger el capital y cobrar ingresos constantes.",
                    "route": ["k401", "etf", "covercall", "escenarios", "analisis", "comando", "videos"]},
    "moderado": {"name": "Moderado", "desc": "Busca crecer con riesgo medido y algo de ingreso.",
                 "route": ["comando", "etf", "analisis", "covercall", "escenarios", "k401", "sectores", "videos"]},
    "crecimiento": {"name": "Crecimiento", "desc": "Acepta más variación a cambio de crecer a largo plazo.",
                    "route": ["sectores", "ranking", "analisis", "etf", "k401", "covercall", "comando"]},
    "activo": {"name": "Activo", "desc": "Opera con frecuencia y busca señales de corto plazo.",
               "route": ["comando", "ranking", "senales", "flujo", "analisis", "desempeno", "covercall", "apalancados"]},
}
QUIZ = [
    ("Para qué plazo inviertes la mayor parte de tu dinero", [("Más de 15 años (retiro)", 0), ("5 a 15 años", 1), ("1 a 5 años", 2), ("Semanas o meses", 3)]),
    ("Si tu cartera cae 20 % en un mes, tú…", [("Vendo para no perder más", 0), ("Me preocupo pero espero", 1), ("Compro más", 2), ("Busco operar la caída", 3)]),
    ("Qué esperas de tus acciones", [("Que no pierdan valor", 0), ("Ingresos constantes (primas)", 1), ("Que crezcan", 2), ("Ganancias rápidas", 3)]),
    ("Cuánto tiempo dedicas a revisar el mercado", [("Casi nada", 0), ("Una vez por semana", 1), ("Cada día", 2), ("Varias veces al día", 3)]),
]


def profile_from_answers(answers) -> str:
    if not isinstance(answers, list) or len(answers) != len(QUIZ) or not all(isinstance(a, int) and 0 <= a <= 3 for a in answers):
        raise ValueError("Responde todas las preguntas")
    avg = sum(answers) / len(answers)
    return "conservador" if avg < 0.75 else "moderado" if avg < 1.5 else "crecimiento" if avg < 2.25 else "activo"


# ---------------------------------------------------------------- preferencias
def pref_get(uid, key, default=None):
    r = db.q1("SELECT value FROM user_prefs WHERE user_id=? AND key=?", (uid, key))
    try:
        return json.loads(r["value"]) if r else default
    except ValueError:
        return default


def pref_set(uid, key, value):
    if key not in PREF_KEYS:
        raise ValueError("Preferencia desconocida")
    blob = json.dumps(value)
    if len(blob) > 20_000:
        raise ValueError("Valor demasiado grande")
    if key == "watch_periods":
        if not isinstance(value, list) or not value or any(v not in analytics.PERIOD_KEYS for v in value):
            raise ValueError("Periodos no válidos")
        value = [k for k in analytics.PERIOD_KEYS if k in value]  # orden estable
        blob = json.dumps(value)
    if key == "profile" and value not in PROFILES:
        raise ValueError("Perfil no válido")
    db.x("INSERT INTO user_prefs(user_id,key,value) VALUES(?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (uid, key, blob))
    return value


# ---------------------------------------------------------------- lista de seguimiento
def watch_symbols(uid):
    return [r["symbol"] for r in db.q("SELECT symbol FROM user_watch WHERE user_id=? ORDER BY added_at, rowid", (uid,))]


def watch_add(uid, syms):
    cur = set(watch_symbols(uid))
    added = 0
    for s in syms:
        s = (s or "").strip().upper()
        if not SYM_RE.match(s):
            raise ValueError(f"Símbolo no válido: {s or '(vacío)'}")
        if s in cur:
            continue
        if len(cur) >= MAX_WATCH:
            raise ValueError(f"Máximo {MAX_WATCH} acciones en tu lista")
        db.x("INSERT INTO user_watch(user_id,symbol,added_at) VALUES(?,?,?)", (uid, s, int(time.time())))
        cur.add(s)
        added += 1
    return added


def watch_remove(uid, sym):
    db.x("DELETE FROM user_watch WHERE user_id=? AND symbol=?", (uid, sym.upper()))


# ---------------------------------------------------------------- estrategias seguidas
def picks(uid):
    return [{"kind": r["kind"], "ref": r["ref"]} for r in db.q("SELECT kind,ref FROM user_picks WHERE user_id=? ORDER BY added_at, rowid", (uid,))]


def pick_set(uid, plan, kind, ref, on):
    from . import strategies
    if kind not in ("core", "cat", "custom"):
        raise ValueError("Tipo no válido")
    ref = str(ref)
    if kind == "core":
        if ref not in strategies.BY_ID or ref not in plans.allowed_strategy_ids(plan):
            raise ValueError("Estrategia no disponible en tu plan")
    elif kind == "cat":
        if not ref.isdigit() or not db.q1("SELECT 1 FROM catalog_strategies WHERE id=?", (int(ref),)):
            raise ValueError("Estrategia no existe")
    else:
        if not ref.isdigit() or not db.q1("SELECT 1 FROM custom_strategies WHERE id=? AND user_id=?", (int(ref), uid)):
            raise ValueError("Estrategia no existe")
    if on:
        if len(picks(uid)) >= 40:
            raise ValueError("Máximo 40 estrategias seguidas")
        db.x("INSERT OR IGNORE INTO user_picks(user_id,kind,ref,added_at) VALUES(?,?,?,?)", (uid, kind, ref, int(time.time())))
    else:
        db.x("DELETE FROM user_picks WHERE user_id=? AND kind=? AND ref=?", (uid, kind, ref))


# ---------------------------------------------------------------- posiciones
def holdings(uid):
    return [dict(r) for r in db.q("SELECT symbol,shares,cost FROM holdings WHERE user_id=? ORDER BY symbol", (uid,))]


def holding_set(uid, sym, shares, cost):
    sym = (sym or "").strip().upper()
    if not SYM_RE.match(sym):
        raise ValueError("Símbolo no válido")
    try:
        shares, cost = float(shares), float(cost)
    except (TypeError, ValueError):
        raise ValueError("Acciones y costo deben ser números")
    if not (0 < shares <= 10_000_000) or not (0 < cost <= 1_000_000):
        raise ValueError("Acciones o costo fuera de rango")
    if not db.q1("SELECT 1 FROM holdings WHERE user_id=? AND symbol=?", (uid, sym)) and len(holdings(uid)) >= MAX_HOLD:
        raise ValueError(f"Máximo {MAX_HOLD} posiciones")
    db.x("INSERT INTO holdings(user_id,symbol,shares,cost) VALUES(?,?,?,?) ON CONFLICT(user_id,symbol) DO UPDATE SET shares=excluded.shares, cost=excluded.cost",
         (uid, sym, shares, cost))


def holding_remove(uid, sym):
    db.x("DELETE FROM holdings WHERE user_id=? AND symbol=?", (uid, sym.upper()))


# ---------------------------------------------------------------- Listas Optionsbb (poco / moderado / alto riesgo)
RISKS = ("low", "mid", "high")
RISK_TITLES = {"low": "Lista Optionsbb · Poco riesgo", "mid": "Lista Optionsbb · Riesgo moderado", "high": "Lista Optionsbb · Alto riesgo"}
DEFAULT_LISTS = {
    "low": ["JNJ", "PG", "KO", "PEP", "WMT", "MCD", "COST", "VZ", "DUK", "SO"],
    "mid": ["MSFT", "AAPL", "GOOGL", "AMZN", "V", "JPM", "HD", "UNH", "LLY", "AVGO"],
    "high": ["TSLA", "NVDA", "AMD", "COIN", "PLTR", "HOOD", "AFRM", "SOFI", "MSTR", "RIVN"],
}


def clean_symbols(syms, limit=MAX_LIST):
    if not isinstance(syms, list):
        raise ValueError("Lista no válida")
    out = []
    for s in syms:
        s = (s or "").strip().upper() if isinstance(s, str) else ""
        if not SYM_RE.match(s):
            raise ValueError(f"Símbolo no válido: {s or '(vacío)'}")
        if s not in out:
            out.append(s)
    if len(out) > limit:
        raise ValueError(f"Máximo {limit} acciones por lista")
    return out


def default_lists():
    """Listas de Optionsbb (el administrador puede cambiarlas); si no hay cambios, las de fábrica."""
    try:
        d = json.loads(db.kv_get("default_lists", "") or "null")
    except ValueError:
        d = None
    if not isinstance(d, dict):
        return {k: list(v) for k, v in DEFAULT_LISTS.items()}
    return {k: (d.get(k) if isinstance(d.get(k), list) else list(DEFAULT_LISTS[k])) for k in RISKS}


def set_default_lists(d):
    if not isinstance(d, dict):
        raise ValueError("Listas no válidas")
    clean = {k: clean_symbols(d.get(k, []) if k in d else DEFAULT_LISTS[k]) for k in RISKS}
    db.kv_set("default_lists", json.dumps(clean))
    return clean


def my_lists(uid):
    d = pref_get(uid, "lists", {}) or {}
    return {k: (d.get(k) if isinstance(d.get(k), list) else []) for k in RISKS}


def set_my_list(uid, risk, syms):
    if risk not in RISKS:
        raise ValueError("Nivel de riesgo no válido")
    syms = clean_symbols(syms)
    cur = my_lists(uid)
    cur[risk] = syms
    pref_set(uid, "lists", cur)
    return syms


# ---------------------------------------------------------------- ETF propio
def _etf_row(r):
    try:
        pos = json.loads(r["positions"])
    except ValueError:
        pos = []
    return {"id": r["id"], "name": r["name"], "positions": pos}


def etfs(uid):
    return [_etf_row(r) for r in db.q("SELECT * FROM user_etfs WHERE user_id=? ORDER BY id", (uid,))]


def etf_get(uid, eid):
    r = db.q1("SELECT * FROM user_etfs WHERE id=? AND user_id=?", (eid, uid))
    return _etf_row(r) if r else None


def etf_create(uid, name):
    name = (name or "").strip()[:60] or "Mi ETF Optionsbb"
    if len(etfs(uid)) >= MAX_ETFS:
        raise ValueError(f"Máximo {MAX_ETFS} ETF propios")
    return db.x("INSERT INTO user_etfs(user_id,name,positions,created_at) VALUES(?,?,?,?)", (uid, name, "[]", int(time.time())))


def etf_save(uid, eid, name, positions):
    """positions ya resueltas: [{symbol, shares, buy_price}]"""
    if not etf_get(uid, eid):
        raise ValueError("ETF no existe")
    if len(positions) > MAX_ETF_POS:
        raise ValueError(f"Máximo {MAX_ETF_POS} acciones por ETF")
    db.x("UPDATE user_etfs SET name=?, positions=? WHERE id=? AND user_id=?", ((name or "").strip()[:60] or "Mi ETF Optionsbb", json.dumps(positions), eid, uid))


def etf_delete(uid, eid):
    db.x("DELETE FROM user_etfs WHERE id=? AND user_id=?", (eid, uid))


# ---------------------------------------------------------------- ETF de Optionsbb (los edita solo el administrador)
OFFICIAL_KEYS = ("low", "mid", "high")
_OFFICIAL_DEFAULT = {
    "low": ("ETF Optionsbb · Poco riesgo", [("JNJ", 6), ("PG", 6), ("KO", 14), ("PEP", 6), ("WMT", 10), ("MCD", 3), ("COST", 1), ("VZ", 22), ("DUK", 8), ("SO", 10)]),
    "mid": ("ETF Optionsbb · Riesgo moderado", [("MSFT", 2), ("AAPL", 4), ("GOOGL", 5), ("AMZN", 5), ("V", 3), ("JPM", 4), ("HD", 3), ("UNH", 3), ("LLY", 1), ("AVGO", 3)]),
    "high": ("ETF Optionsbb · Alto riesgo", [("TSLA", 3), ("NVDA", 6), ("AMD", 6), ("COIN", 3), ("PLTR", 6), ("HOOD", 10), ("AFRM", 15), ("SOFI", 40), ("MSTR", 3), ("RIVN", 70)]),
}


def official_etfs():
    try:
        d = json.loads(db.kv_get("official_etfs", "") or "null")
    except ValueError:
        d = None
    out = {}
    for k in OFFICIAL_KEYS:
        if isinstance(d, dict) and isinstance(d.get(k), dict) and d[k].get("positions"):
            out[k] = {"key": k, "name": d[k]["name"], "positions": d[k]["positions"]}
        else:
            nm, pos = _OFFICIAL_DEFAULT[k]
            out[k] = {"key": k, "name": nm, "positions": [{"symbol": s, "shares": n} for s, n in pos]}
    return out


def set_official_etfs(d):
    if not isinstance(d, dict):
        raise ValueError("Datos no válidos")
    cur = official_etfs()
    for k in OFFICIAL_KEYS:
        if k not in d:
            continue
        e = d[k]
        if not isinstance(e, dict) or not isinstance(e.get("positions"), list) or not e["positions"]:
            raise ValueError("Cada ETF necesita al menos una acción")
        if len(e["positions"]) > MAX_ETF_POS:
            raise ValueError(f"Máximo {MAX_ETF_POS} acciones por ETF")
        seen, pos = set(), []
        for p in e["positions"]:
            s = str((p or {}).get("symbol") or "").strip().upper()
            if not SYM_RE.match(s):
                raise ValueError(f"Símbolo no válido: {s or '(vacío)'}")
            if s in seen:
                raise ValueError(f"{s} está repetida")
            try:
                n = float(p.get("shares"))
            except (TypeError, ValueError):
                raise ValueError(f"Acciones no válidas en {s}")
            if not (0 < n <= 1_000_000):
                raise ValueError(f"Acciones fuera de rango en {s}")
            seen.add(s)
            pos.append({"symbol": s, "shares": n})
        cur[k] = {"key": k, "name": str(e.get("name") or cur[k]["name"]).strip()[:60], "positions": pos}
    db.kv_set("official_etfs", json.dumps({k: {"name": v["name"], "positions": v["positions"]} for k, v in cur.items()}))
    return cur
