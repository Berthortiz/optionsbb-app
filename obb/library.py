"""Biblioteca de videos (YouTube), estrategias personalizadas y catálogo de señales de mentores."""
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from . import config, db, plans, rules

YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
CATEGORIES = ["General", "Cover Call", "Thinkorswim", "Estrategias", "Opciones", "Psicología", "Análisis"]


class LibError(ValueError):
    pass


# ---------------------------------------------------------------- videos
def extract_id(text: str) -> str:
    t = (text or "").strip()
    if YT_ID.match(t):
        return t
    try:
        u = urllib.parse.urlparse(t if "//" in t else "https://" + t)
    except ValueError:
        raise LibError("Enlace de YouTube no válido")
    host = (u.hostname or "").lower()
    if host in ("youtu.be", "www.youtu.be"):
        cand = u.path.strip("/").split("/")[0]
    elif host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        qs = urllib.parse.parse_qs(u.query)
        if qs.get("v"):
            cand = qs["v"][0]
        else:
            m = re.match(r"^/(?:shorts|embed|live|v)/([^/?]+)", u.path)
            cand = m.group(1) if m else ""
    else:
        raise LibError("El enlace debe ser de YouTube")
    if not YT_ID.match(cand or ""):
        raise LibError("No encontré el ID del video en el enlace")
    return cand


def _oembed_title(yt_id):
    try:
        url = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(f"https://www.youtube.com/watch?v={yt_id}", safe="")
        with urllib.request.urlopen(url, timeout=6) as r:
            return json.loads(r.read()).get("title")
    except Exception:
        return None


def add_video(url, title="", description="", category="General", min_plan="basico"):
    yt = extract_id(url)
    if not plans.valid(min_plan):
        raise LibError("Plan no válido")
    category = (category or "General").strip()[:40] or "General"
    title = (title or "").strip()[:160] or _oembed_title(yt) or f"Video {yt}"
    if db.q1("SELECT 1 FROM videos WHERE yt_id=?", (yt,)):
        raise LibError("Ese video ya está en la biblioteca")
    vid = db.x("INSERT INTO videos(yt_id,title,description,category,min_plan,created_at) VALUES(?,?,?,?,?,?)",
               (yt, title, (description or "").strip()[:600], category, min_plan, int(time.time())))
    return vid


def update_video(vid, d):
    row = db.q1("SELECT * FROM videos WHERE id=?", (vid,))
    if not row:
        raise LibError("El video no existe")
    title = (d.get("title", row["title"]) or "").strip()[:160] or row["title"]
    desc = (d.get("description", row["description"]) or "").strip()[:600]
    cat = (d.get("category", row["category"]) or "General").strip()[:40] or "General"
    mp = d.get("min_plan", row["min_plan"])
    if not plans.valid(mp):
        raise LibError("Plan no válido")
    db.x("UPDATE videos SET title=?,description=?,category=?,min_plan=? WHERE id=?", (title, desc, cat, mp, vid))


def delete_video(vid):
    db.x("DELETE FROM videos WHERE id=?", (vid,))


def parse_feed(xml_bytes: bytes) -> list:
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    out = []
    for e in ET.fromstring(xml_bytes).findall("a:entry", ns):
        yid = e.findtext("yt:videoId", namespaces=ns)
        if yid and YT_ID.match(yid):
            out.append({"yt_id": yid, "title": (e.findtext("a:title", namespaces=ns) or yid)[:160],
                        "published": (e.findtext("a:published", namespaces=ns) or "")[:10]})
    return out


def sync_channel(fetch=None) -> dict:
    """Importa los últimos videos del canal (RSS público de YouTube; requiere OBB_YT_CHANNEL_ID)."""
    if not config.YT_CHANNEL_ID or not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", config.YT_CHANNEL_ID):
        raise LibError("Configura OBB_YT_CHANNEL_ID (el ID del canal, empieza con UC…) para sincronizar automáticamente")
    url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + config.YT_CHANNEL_ID
    try:
        data = fetch(url) if fetch else urllib.request.urlopen(url, timeout=10).read()
    except Exception as e:
        raise LibError(f"No se pudo leer el canal de YouTube: {e}")
    new = 0
    for v in parse_feed(data):
        if not db.q1("SELECT 1 FROM videos WHERE yt_id=?", (v["yt_id"],)):
            db.x("INSERT INTO videos(yt_id,title,category,min_plan,published,created_at) VALUES(?,?,?,?,?,?)",
                 (v["yt_id"], v["title"], "General", "basico", v["published"], int(time.time())))
            new += 1
    return {"added": new}


def list_videos(plan: str, admin: bool) -> list:
    out = []
    for r in db.q("SELECT * FROM videos ORDER BY COALESCE(published,'') DESC, id DESC LIMIT 500"):
        locked = not plans.at_least(plan, r["min_plan"]) and not admin
        d = {"id": r["id"], "title": r["title"], "description": r["description"], "category": r["category"],
             "min_plan": r["min_plan"], "min_plan_name": plans.PLANS[r["min_plan"]]["name"], "locked": locked,
             "published": r["published"]}
        if not locked:  # un video bloqueado no revela su ID
            d["yt_id"] = r["yt_id"]
        out.append(d)
    return out


# ---------------------------------------------------------------- estrategias personalizadas
def _clean_name(name):
    name = re.sub(r"\s+", " ", (name or "")).strip()
    if not 2 <= len(name) <= 40:
        raise LibError("El nombre debe tener entre 2 y 40 caracteres")
    return name


def list_custom(uid):
    return [{"id": r["id"], "name": r["name"], "side": r["side"], "rule": json.loads(r["rule"]),
             "text": rules.describe(json.loads(r["rule"]))} for r in db.q("SELECT * FROM custom_strategies WHERE user_id=? ORDER BY id", (uid,))]


def add_custom(uid, plan, name, rule):
    limit = plans.CUSTOM_LIMIT[plan]
    if limit <= 0:
        raise LibError("Tu plan no incluye estrategias personalizadas")
    if db.q1("SELECT COUNT(*) n FROM custom_strategies WHERE user_id=?", (uid,))["n"] >= limit:
        raise LibError(f"Tu plan permite {limit} estrategias personalizadas. Elimina una para crear otra.")
    try:
        r = rules.validate(rule)
    except rules.RuleError as e:
        raise LibError(str(e))
    return db.x("INSERT INTO custom_strategies(user_id,name,side,rule,created_at) VALUES(?,?,?,?,?)",
                (uid, _clean_name(name), r["side"], json.dumps(r), int(time.time())))


def delete_custom(uid, sid):
    db.x("DELETE FROM custom_strategies WHERE id=? AND user_id=?", (sid, uid))


# ---------------------------------------------------------------- catálogo de mentores (lo administra el admin)
SEED = [
    ("Cruce 9/21 con volumen", "BULL", "Cruce alcista de medias con volumen superior al promedio.",
     [{"type": "sma_cross", "fast": 9, "slow": 21, "dir": "up"}, {"type": "volume_spike", "mult": 1.5, "n": 20}]),
    ("Rebote por sobreventa", "BULL", "RSI bajo 30 y vela verde de reversión.",
     [{"type": "rsi", "n": 14, "op": "lt", "value": 30}, {"type": "candle", "color": "green", "min_body_pct": 40}]),
    ("Ruptura de 20 velas con volumen", "BULL", "Cierre sobre el máximo de 20 velas con volumen explosivo.",
     [{"type": "breakout", "n": 20, "dir": "up"}, {"type": "volume_spike", "mult": 2, "n": 20}]),
    ("Impulso sobre SMA 21", "BULL", "Precio sobre la SMA 21 y avance de 1.5 % en 6 velas.",
     [{"type": "price_sma", "n": 21, "dir": "above"}, {"type": "pct_move", "bars": 6, "op": "gt", "pct": 1.5}]),
    ("Cruce 9/21 bajista con volumen", "BEAR", "Cruce bajista de medias con volumen superior al promedio.",
     [{"type": "sma_cross", "fast": 9, "slow": 21, "dir": "down"}, {"type": "volume_spike", "mult": 1.5, "n": 20}]),
    ("Rechazo por sobrecompra", "BEAR", "RSI sobre 70 y vela roja de reversión.",
     [{"type": "rsi", "n": 14, "op": "gt", "value": 70}, {"type": "candle", "color": "red", "min_body_pct": 40}]),
    ("Ruptura de soporte con volumen", "BEAR", "Cierre bajo el mínimo de 20 velas con volumen explosivo.",
     [{"type": "breakout", "n": 20, "dir": "down"}, {"type": "volume_spike", "mult": 2, "n": 20}]),
    ("Caída bajo SMA 21", "BEAR", "Precio bajo la SMA 21 y caída de 1.5 % en 6 velas.",
     [{"type": "price_sma", "n": 21, "dir": "below"}, {"type": "pct_move", "bars": 6, "op": "lt", "pct": -1.5}]),
]


def seed_catalog():
    if db.q1("SELECT 1 FROM catalog_strategies LIMIT 1"):
        return
    for name, side, desc, conds in SEED:
        db.x("INSERT INTO catalog_strategies(name,source,language,side,description,rule,created_at) VALUES(?,?,?,?,?,?,?)",
             (name, "Clásica (genérica)", "ES", side, desc, json.dumps(rules.validate({"side": side, "conditions": conds})), int(time.time())))


def list_catalog():
    out = []
    for r in db.q("SELECT * FROM catalog_strategies ORDER BY id"):
        rule = json.loads(r["rule"])
        out.append({"id": r["id"], "name": r["name"], "source": r["source"], "language": r["language"], "side": r["side"],
                    "description": r["description"], "rule": rule, "text": rules.describe(rule)})
    return out


def add_catalog(d):
    try:
        r = rules.validate(d.get("rule"))
    except rules.RuleError as e:
        raise LibError(str(e))
    lang = d.get("language", "ES")
    if lang not in ("ES", "EN"):
        raise LibError("Idioma no válido")
    return db.x("INSERT INTO catalog_strategies(name,source,language,side,description,rule,created_at) VALUES(?,?,?,?,?,?,?)",
                (_clean_name(d.get("name")), (d.get("source") or "")[:60], lang, r["side"], (d.get("description") or "")[:300],
                 json.dumps(r), int(time.time())))


def delete_catalog(cid):
    db.x("DELETE FROM catalog_strategies WHERE id=?", (cid,))
