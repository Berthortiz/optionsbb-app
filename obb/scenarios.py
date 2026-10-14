"""Datos de los módulos «¿Qué hubiera pasado si…?» y «Apalancados + Cover Call».
Los ejemplos usan trayectorias ILUSTRATIVAS (precios redondeados, no históricos exactos): el usuario puede editarlas
con los precios reales o, con Schwab conectado, usar el historial real de cualquier símbolo."""

CATEGORIES = ["Casos de estudio", "Mis casos"]

EXAMPLES = [
    {"id": "bynd", "category": "Cae mes tras mes", "symbol": "BYND", "title": "BYND: una acción que cae mes tras mes",
     "story": "Compras 1.000 acciones cerca de $7 y la acción pierde valor casi todos los meses. Esperar a que se «recupere» no pagó nada. "
              "Con cover call, cada mes cobras la prima de un call fuera del dinero y esa prima amortiza parte de la caída.",
     "shares": 1000, "otm": 10, "iv": 120, "prices": [7.0, 5.9, 5.1, 4.6, 3.9, 3.2, 2.9, 2.4, 2.0, 1.6, 1.4, 1.2, 1.1]},
    {"id": "msft", "category": "Lateral o retrocede", "symbol": "MSFT", "title": "MSFT: una gran empresa que se queda quieta o retrocede",
     "story": "Compras 100 acciones de una empresa sólida y el precio se mueve de lado o baja un poco durante el año. "
              "Sin cover call tus acciones esperan inactivas; con cover call generan un ingreso mensual mientras esperas.",
     "shares": 100, "otm": 5, "iv": 25, "prices": [520, 505, 488, 470, 452, 440, 447, 455, 442, 430, 438, 445, 440]},
    {"id": "lateral", "category": "Lateral o retrocede", "symbol": "EJEMPLO", "title": "Acción lateral: sube y baja sin ir a ningún lado",
     "story": "El precio da vueltas alrededor de $100 durante un año. Quien solo tiene las acciones termina casi igual; quien vende un call cada mes cobra una prima en cada ciclo. Es el escenario donde el cover call brilla.",
     "shares": 100, "otm": 5, "iv": 28, "prices": [100, 102, 99, 101, 98, 100, 103, 99, 97, 101, 100, 102, 100]},
    {"id": "tranquila", "category": "Lateral o retrocede", "symbol": "EJEMPLO", "title": "Empresa tranquila que paga dividendo (sube poco)",
     "story": "Una acción estable que sube apenas un 4 % en el año. Se vende un call poco volátil: la prima es pequeña, pero constante, y se suma al dividendo.",
     "shares": 200, "otm": 4, "iv": 18, "prices": [60, 60.4, 60.9, 60.5, 61.2, 61.6, 61.3, 61.9, 62.2, 61.8, 62.4, 62.1, 62.4]},
    {"id": "rebote", "category": "Cae y se recupera", "symbol": "EJEMPLO", "title": "Caída fuerte y rebote (forma de V)",
     "story": "La acción cae un 35 % en cuatro meses y luego se recupera. Las primas más altas durante la caída amortiguan la pérdida; en el rebote, el call limita parte de la subida.",
     "shares": 100, "otm": 7, "iv": 60, "prices": [100, 92, 80, 70, 65, 72, 80, 88, 95, 99, 103, 104, 106]},
    {"id": "crisis", "category": "Cae y se recupera", "symbol": "EJEMPLO", "title": "Crisis de mercado: -30 % y regreso al punto de partida",
     "story": "Un año de miedo: el precio se desploma y tarda meses en volver. Las acciones solas parecen «empatar» al final, pero durante el camino el cover call fue cobrando primas.",
     "shares": 100, "otm": 8, "iv": 50, "prices": [100, 94, 85, 74, 70, 73, 78, 83, 88, 93, 97, 99, 100]},
    {"id": "rally", "category": "Sube con fuerza", "symbol": "EJEMPLO", "title": "Subida fuerte: el límite del cover call",
     "story": "La acción sube un 60 % en el año. Aquí el cover call cobra primas pero limita la ganancia cuando te ejercen: es el costo de la estrategia, y conviene verlo antes de usarla.",
     "shares": 100, "otm": 5, "iv": 45, "prices": [100, 106, 113, 119, 126, 131, 138, 143, 149, 152, 156, 159, 160]},
    {"id": "montana", "category": "Muy volátil", "symbol": "EJEMPLO", "title": "Montaña rusa: sube y baja con fuerza",
     "story": "Cambios de ±15 % cada mes. La volatilidad alta paga primas altas, pero también te ejercen o pierdes con más frecuencia. Mira cuánto compensa.",
     "shares": 100, "otm": 10, "iv": 85, "prices": [100, 118, 99, 120, 96, 115, 94, 118, 100, 122, 101, 120, 104]},
    {"id": "apalancado", "category": "Muy volátil", "symbol": "EJEMPLO", "title": "ETF apalancado 2x en un mercado de lado",
     "story": "Un ETF apalancado pierde valor por decadencia aunque el activo base termine igual. Con cover call se cobran primas muy altas que compensan parte de esa pérdida (ver el módulo Apalancados + CC).",
     "shares": 100, "otm": 10, "iv": 95, "prices": [100, 108, 97, 104, 93, 99, 90, 96, 88, 92, 85, 90, 84]},
]


def _num(v, name, lo, hi):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{name} debe ser un número")
    if not lo <= x <= hi:
        raise ValueError(f"{name} debe estar entre {lo:g} y {hi:g}")
    return x


def clean_case(d: dict) -> dict:
    """Valida un caso guardado (de usuario o de administrador)."""
    title = str(d.get("title") or d.get("name") or "").strip()[:60]
    if not title:
        raise ValueError("Ponle un nombre al caso")
    raw = d.get("prices")
    if isinstance(raw, str):
        raw = [x for x in raw.replace(";", ",").replace("\n", ",").replace(" ", ",").split(",") if x]
    if not isinstance(raw, list) or not 2 <= len(raw) <= 61:
        raise ValueError("Escribe entre 2 y 61 precios")
    prices = [_num(x, "Precio", 0.0001, 1e7) for x in raw]
    sym = str(d.get("symbol") or "EJEMPLO").strip().upper()[:8] or "EJEMPLO"
    return {"title": title, "category": str(d.get("category") or "Casos de estudio").strip()[:40],
            "story": str(d.get("story") or "").strip()[:500], "symbol": sym,
            "shares": _num(d.get("shares"), "Acciones", 1, 10_000_000), "otm": _num(d.get("otm", 5), "Call fuera del dinero %", 0, 50),
            "iv": _num(d.get("iv", 30), "Volatilidad", 5, 300), "prices": prices}


def admin_cases():
    from . import db
    import json
    try:
        return json.loads(db.kv_get("whatif_cases", "[]") or "[]")
    except ValueError:
        return []


def save_admin_cases(lst):
    from . import db
    import json
    db.kv_set("whatif_cases", json.dumps(lst))


def all_official():
    return EXAMPLES + [dict(c, kind="admin") for c in admin_cases()]


# Instrumentos apalancados populares. «leverage» es el múltiplo diario del activo base.
LEVERAGED = [
    {"symbol": "NVDL", "name": "2x NVIDIA", "base": "NVDA", "leverage": 2},
    {"symbol": "AMDL", "name": "2x AMD", "base": "AMD", "leverage": 2},
    {"symbol": "TSLL", "name": "2x Tesla", "base": "TSLA", "leverage": 2},
    {"symbol": "CONL", "name": "2x Coinbase", "base": "COIN", "leverage": 2},
    {"symbol": "MSTU", "name": "2x MicroStrategy", "base": "MSTR", "leverage": 2},
    {"symbol": "PLTU", "name": "2x Palantir", "base": "PLTR", "leverage": 2},
    {"symbol": "TQQQ", "name": "3x Nasdaq-100", "base": "QQQ", "leverage": 3},
    {"symbol": "SOXL", "name": "3x semiconductores", "base": "SOXX", "leverage": 3},
    {"symbol": "SPXL", "name": "3x S&P 500", "base": "SPY", "leverage": 3},
]
