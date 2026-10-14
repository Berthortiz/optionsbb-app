#!/usr/bin/env python3
"""OPTIONS BB · Centro de Comando — servidor web (solo librería estándar de Python 3.10+).

    python server.py                         arranca la app
    python server.py create-admin EMAIL      crea el usuario administrador
    python server.py import-watchlist X.xlsx carga las acciones por sector desde Excel
    python server.py schwab-login            conecta tu cuenta de Schwab (OAuth)
"""
import getpass
import json
import logging
import mimetypes
import re
import secrets
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from obb import analytics, auth, billing, config, covercall, db, flow, guide, optcalc, k401, library, plans, overlay, providers, referrals, reports, rules, scenarios, service, userdata, version

log = logging.getLogger("obb")
SESSION_COOKIE = "obb_session"
SYM_RE = service.SYM_RE
_lo = urllib.parse.urlparse(config.LOGO_URL.replace("{SYM}", "X"))
LOGO_ORIGIN = f"{_lo.scheme}://{_lo.netloc}" if _lo.scheme in ("http", "https") and _lo.netloc else ""


class HttpError(Exception):
    def __init__(self, code, msg, extra=None):
        super().__init__(msg)
        self.code, self.msg, self.extra = code, msg, extra or {}


class Handler(BaseHTTPRequestHandler):
    server_version = "OptionsBB"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *a):
        log.debug("%s %s", self.address_string(), fmt % a)

    # ------------------------------------------------------------ utilidades
    def _headers(self, ctype, length, extra=None, cache="no-store"):
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        if ctype.startswith("text/html"):
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; img-src 'self' data: https://i.ytimg.com https://www.google.com https://*.gstatic.com "+LOGO_ORIGIN+"; frame-src https://www.youtube-nocookie.com; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()

    def send_bytes(self, code, body, ctype, extra=None, cache="no-store"):
        self.send_response(code)
        self._headers(ctype, len(body), extra, cache)
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_json(self, code, obj, extra=None):
        self.send_bytes(code, json.dumps(obj, ensure_ascii=False, allow_nan=False, default=str).encode(), "application/json; charset=utf-8", extra)

    def read_body(self, limit=1_000_000) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        if n > limit:
            raise HttpError(413, "Archivo demasiado grande")
        return self.rfile.read(n) if n else b""

    def read_json(self) -> dict:
        try:
            d = json.loads(self.read_body(1_000_000) or b"{}")
            return d if isinstance(d, dict) else {}
        except json.JSONDecodeError:
            raise HttpError(400, "JSON no válido")

    def client_ip(self):
        if config.env("OBB_TRUST_PROXY") == "1":
            return (self.headers.get("X-Forwarded-For") or "").split(",")[0].strip() or self.client_address[0]
        return self.client_address[0]

    def cookie(self, name):
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == name:
                return v
        return None

    def current_user(self):
        tok = self.cookie(SESSION_COOKIE)
        uid = auth.read_token(tok) if tok else None
        return auth.get_user(uid) if uid else None

    def need_user(self):
        u = self.current_user()
        if not u:
            raise HttpError(401, "Inicia sesión")
        return u

    def need_access(self):
        u = self.need_user()
        info = auth.access_info(u)
        if not info["access"]:
            raise HttpError(402, "Tu prueba o suscripción no está activa", {"reason": info["reason"]})
        return u

    def need_module(self, module):
        u = self.need_access()
        p = plans.effective_plan(u)
        if not plans.has_module(p, module):
            need = plans.MODULE_MIN[module]
            raise HttpError(403, f"Este módulo es del plan {plans.PLANS[need]['name']} o superior", {"reason": "plan", "need": need, "plan": p})
        return u, p

    def need_admin(self):
        u = self.need_user()
        if u["role"] != "admin":
            raise HttpError(403, "Solo administradores")
        return u

    def session_cookie(self, token, max_age):
        flags = f"Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}" + ("; Secure" if config.COOKIE_SECURE else "")
        return {"Set-Cookie": f"{SESSION_COOKIE}={token}; {flags}"}

    # ------------------------------------------------------------ despacho
    def do_HEAD(self):
        self.dispatch("GET")

    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def do_DELETE(self):
        self.dispatch("DELETE")

    def do_PUT(self):
        self.dispatch("PUT")

    def dispatch(self, method):
        try:
            url = urllib.parse.urlparse(self.path)
            path, qs = url.path, urllib.parse.parse_qs(url.query)
            if path.startswith("/api/"):
                if method in ("POST", "PUT", "DELETE") and path != "/api/billing/webhook" and self.headers.get("X-OBB") != "1":
                    raise HttpError(403, "Petición no permitida")
                self.api(method, path, qs)
            elif method == "GET":
                self.static(path)
            else:
                raise HttpError(405, "Método no permitido")
        except HttpError as e:
            self.send_json(e.code, {"error": e.msg, **e.extra})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            log.exception("error en %s %s", method, self.path)
            self.send_json(500, {"error": "Error interno del servidor"})

    def static(self, path):
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        f = (config.STATIC_DIR / rel).resolve()
        if not str(f).startswith(str(config.STATIC_DIR.resolve())) or not f.is_file():
            raise HttpError(404, "No encontrado")
        ctype = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        self.send_bytes(200, f.read_bytes(), ctype, cache="no-cache")

    # ------------------------------------------------------------ API
    def api(self, method, path, qs):
        S = service.SERVICE
        q1 = lambda k, d="": (qs.get(k) or [d])[0]

        if path == "/api/config" and method == "GET":
            return self.send_json(200, {"version": version.VERSION, "trial_days": config.TRIAL_DAYS, "billing": billing.configured(), "plans": plans.catalog(),
                                        "links": {"youtube": config.YT_CHANNEL_URL, "web": config.WEBSITE_URL, "logo": config.LOGO_URL}})

        # ---- sesión ----
        if path == "/api/auth/register" and method == "POST":
            d = self.read_json()
            ip = self.client_ip()
            if auth.too_many_attempts("reg:" + ip, limit=10, window=3600):
                raise HttpError(429, "Demasiados registros desde esta red. Intenta más tarde.")
            auth.register_fail("reg:" + ip)
            try:
                u = auth.create_user(d.get("email"), d.get("password"), d.get("name", ""), plan=d.get("plan") or "avanzado", ref=d.get("ref"))
            except ValueError as e:
                raise HttpError(400, str(e))
            return self.send_json(201, {"user": auth.public_user(u)}, self.session_cookie(auth.make_token(u["id"]), 30 * 86400))
        if path == "/api/auth/login" and method == "POST":
            d = self.read_json()
            email = (d.get("email") or "").strip().lower()
            key = f"{self.client_ip()}|{email}"
            if auth.too_many_attempts(key):
                raise HttpError(429, "Demasiados intentos. Espera 10 minutos.")
            u = auth.get_user_by_email(email)
            if not u or not auth.verify_pw(d.get("password") or "", u["pw_hash"]):
                auth.register_fail(key)
                raise HttpError(401, "Correo o contraseña incorrectos")
            auth.clear_fails(key)
            return self.send_json(200, {"user": auth.public_user(u)}, self.session_cookie(auth.make_token(u["id"]), 30 * 86400))
        if path == "/api/auth/logout" and method == "POST":
            return self.send_json(200, {"ok": True}, self.session_cookie("", 0))
        if path == "/api/me" and method == "GET":
            u = self.need_user()
            return self.send_json(200, {"user": auth.public_user(u), "billing": billing.configured(), "trial_days": config.TRIAL_DAYS,
                                        "plans": plans.catalog(plans.effective_plan(u)),
                                        "links": {"youtube": config.YT_CHANNEL_URL, "web": config.WEBSITE_URL, "logo": config.LOGO_URL}})

        # ---- cobro ----
        if path == "/api/billing/checkout" and method == "POST":
            try:
                pl = self.read_json().get("plan")
                return self.send_json(200, {"url": billing.checkout_url(self.need_user(), pl)})
            except billing.BillingError as e:
                raise HttpError(503, str(e))
        if path == "/api/billing/portal" and method == "POST":
            try:
                return self.send_json(200, {"url": billing.portal_url(self.need_user())})
            except billing.BillingError as e:
                raise HttpError(503, str(e))
        if path == "/api/billing/webhook" and method == "POST":
            body = self.read_body(500_000)
            if not config.STRIPE_WEBHOOK_SECRET or not billing.verify_signature(body, self.headers.get("Stripe-Signature", ""), config.STRIPE_WEBHOOK_SECRET):
                raise HttpError(400, "Firma no válida")
            result = billing.handle_event(json.loads(body))
            return self.send_json(200, {"ok": True, "result": result})

        # ---- datos (requieren prueba o suscripción activa) ----
        if path == "/api/command" and method == "GET":
            u, pl = self.need_module("comando")
            return self.send_json(200, S.command(set(plans.allowed_strategy_ids(pl))))
        if path == "/api/sectors" and method == "GET":
            u, pl = self.need_module("sectores")
            return self.send_json(200, S.sectors_view(set(plans.allowed_strategy_ids(pl))))
        if path == "/api/chart" and method == "GET":
            u, pl = self.need_module("comando")
            sym = q1("symbol", "SPY").upper()
            okids = set(plans.allowed_strategy_ids(pl))
            ids = lambda k: [x for x in q1(k).split(",") if re.fullmatch(r"[a-z_]+", x) and x in okids]
            try:
                return self.send_json(200, S.chart(sym, q1("range", "1D"), ids("bull"), ids("bear")))
            except ValueError as e:
                raise HttpError(400, str(e))
            except providers.ProviderError as e:
                raise HttpError(503, str(e))
        if path == "/api/oi-flow" and method == "GET":
            self.need_module("flujo")
            pairs = flow.available_pairs()
            if not pairs:
                return self.send_json(200, {"pairs": [], "result": None, "status": S.status()})
            c, m = q1("close"), q1("morning")
            sel = next((p for p in pairs if p["close_date"] == c and p["morning_date"] == m), pairs[0])
            return self.send_json(200, {"pairs": pairs, "result": flow.compute(sel["close_date"], sel["morning_date"]), "status": S.status()})

        # ---- reporte de desempeño ----
        if path == "/api/reports" and method == "GET":
            self.need_module("desempeno")
            return self.send_json(200, {"reports": reports.list_reports()})
        m = re.fullmatch(r"/api/reports/(\d+)(/xlsx)?", path)
        if m and method == "GET":
            self.need_module("desempeno")
            rep = reports.load_report(int(m.group(1)))
            if not rep:
                raise HttpError(404, "Reporte no existe")
            if m.group(2):
                try:
                    data = reports.to_xlsx(rep)
                except ImportError:
                    raise HttpError(501, "Para exportar a Excel instala openpyxl: python -m pip install openpyxl")
                name = f"Reporte_Estrategias_OptionsBB_{rep['meta']['symbol'] or 'ALL'}_{m.group(1)}.xlsx"
                return self.send_bytes(200, data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                       {"Content-Disposition": f'attachment; filename="{name}"'})
            return self.send_json(200, rep)
        if m and method == "DELETE" and not m.group(2):
            self.need_admin()
            reports.delete_report(int(m.group(1)))
            return self.send_json(200, {"ok": True})

        # ---- Cover Call ----
        if path.startswith("/api/cc/"):
            u, pl = self.need_module("covercall")
            try:
                if path == "/api/cc/chain-parse" and method == "POST":
                    rows, warns = covercall.parse_chain_text(str(self.read_json().get("text", ""))[:60_000])
                    return self.send_json(200, {"chain": rows, "warnings": warns})
                if path == "/api/cc/analyze" and method == "POST":
                    return self.send_json(200, covercall.analyze(self.read_json()))
                if path == "/api/cc/simulate" and method == "POST":
                    d = self.read_json()
                    return self.send_json(200, covercall.simulate_wheel(d.get("params") or {}, d.get("cycles") or []))
                if path == "/api/cc/sims" and method == "GET":
                    rows = db.q("SELECT id,name,created_at FROM cc_sims WHERE user_id=? ORDER BY id DESC LIMIT 100", (u["id"],))
                    return self.send_json(200, {"sims": [dict(r) for r in rows]})
                if path == "/api/cc/sims" and method == "POST":
                    d = self.read_json()
                    name = re.sub(r"\s+", " ", str(d.get("name") or "")).strip()[:60] or "Simulación"
                    payload = json.dumps({"params": d.get("params") or {}, "cycles": d.get("cycles") or []})
                    if len(payload) > 900_000:
                        raise HttpError(400, "La simulación es demasiado grande")
                    if db.q1("SELECT COUNT(*) n FROM cc_sims WHERE user_id=?", (u["id"],))["n"] >= 100:
                        raise HttpError(400, "Máximo 100 simulaciones guardadas")
                    sid = db.x("INSERT INTO cc_sims(user_id,name,created_at,payload) VALUES(?,?,?,?)", (u["id"], name, int(time.time()), payload))
                    return self.send_json(201, {"id": sid})
                m = re.fullmatch(r"/api/cc/sims/(\d+)", path)
                if m and method == "GET":
                    r = db.q1("SELECT * FROM cc_sims WHERE id=? AND user_id=?", (int(m.group(1)), u["id"]))
                    if not r:
                        raise HttpError(404, "Simulación no existe")
                    return self.send_json(200, {"id": r["id"], "name": r["name"], **json.loads(r["payload"])})
                if m and method == "DELETE":
                    db.x("DELETE FROM cc_sims WHERE id=? AND user_id=?", (int(m.group(1)), u["id"]))
                    return self.send_json(200, {"ok": True})
            except covercall.CCError as e:
                raise HttpError(400, str(e))

        # ---- videos ----
        if path == "/api/videos" and method == "GET":
            u, pl = self.need_module("videos")
            return self.send_json(200, {"videos": library.list_videos(pl, u["role"] == "admin"), "categories": library.CATEGORIES,
                                        "links": {"youtube": config.YT_CHANNEL_URL, "web": config.WEBSITE_URL},
                                        "can_sync": bool(config.YT_CHANNEL_ID)})
        if path.startswith("/api/admin/videos"):
            self.need_admin()
            try:
                if path == "/api/admin/videos" and method == "POST":
                    d = self.read_json()
                    return self.send_json(201, {"id": library.add_video(d.get("url"), d.get("title"), d.get("description"), d.get("category"), d.get("min_plan", "basico"))})
                if path == "/api/admin/videos/sync" and method == "POST":
                    return self.send_json(200, library.sync_channel())
                m = re.fullmatch(r"/api/admin/videos/(\d+)", path)
                if m and method == "POST":
                    library.update_video(int(m.group(1)), self.read_json())
                    return self.send_json(200, {"ok": True})
                if m and method == "DELETE":
                    library.delete_video(int(m.group(1)))
                    return self.send_json(200, {"ok": True})
            except library.LibError as e:
                raise HttpError(400, str(e))

        # ---- señales (Avanzado): catálogo de mentores + estrategias personalizadas ----
        if path == "/api/signals" and method == "GET":
            u, pl = self.need_module("senales")
            out = S.signals_view(u["id"], pl)
            out["custom_limit"] = plans.CUSTOM_LIMIT[pl]
            return self.send_json(200, out)
        if path == "/api/custom" and method == "POST":
            u, pl = self.need_module("senales")
            d = self.read_json()
            try:
                cid = library.add_custom(u["id"], pl, d.get("name"), d.get("rule"))
            except library.LibError as e:
                raise HttpError(400, str(e))
            return self.send_json(201, {"id": cid})
        m = re.fullmatch(r"/api/custom/(\d+)", path)
        if m and method == "DELETE":
            u, pl = self.need_module("senales")
            library.delete_custom(u["id"], int(m.group(1)))
            return self.send_json(200, {"ok": True})
        if path == "/api/admin/catalog" and method == "POST":
            self.need_admin()
            try:
                return self.send_json(201, {"id": library.add_catalog(self.read_json())})
            except library.LibError as e:
                raise HttpError(400, str(e))
        m = re.fullmatch(r"/api/admin/catalog/(\d+)", path)
        if m and method == "DELETE":
            self.need_admin()
            library.delete_catalog(int(m.group(1)))
            return self.send_json(200, {"ok": True})
        if path == "/api/admin/plan-price" and method == "POST":
            self.need_admin()
            d = self.read_json()
            if not plans.valid(d.get("plan")):
                raise HttpError(400, "Plan no válido")
            db.kv_set("plan_price_" + d["plan"], str(d.get("label") or "")[:40])
            return self.send_json(200, {"plans": plans.catalog()})

        # ---- Inicio / preferencias ----
        if path == "/api/prefs" and method == "GET":
            u, pl = self.need_module("inicio")
            return self.send_json(200, {"profile": userdata.pref_get(u["id"], "profile"), "k401": userdata.pref_get(u["id"], "k401", {}),
                                        "profiles": {k: {"name": v["name"], "desc": v["desc"], "route": [m for m in v["route"] if plans.has_module(pl, m)],
                                                         "locked": [m for m in v["route"] if not plans.has_module(pl, m)]} for k, v in userdata.PROFILES.items()},
                                        "quiz": [{"q": q, "opts": [o for o, _ in opts]} for q, opts in userdata.QUIZ]})
        if path == "/api/prefs" and method == "POST":
            u, pl = self.need_module("inicio")
            d = self.read_json()
            try:
                if "answers" in d:
                    d = {"key": "profile", "value": userdata.profile_from_answers(d["answers"])}
                v = userdata.pref_set(u["id"], d.get("key"), d.get("value"))
            except ValueError as e:
                raise HttpError(400, str(e))
            return self.send_json(200, {"key": d["key"], "value": v})

        # ---- lista de seguimiento personal ----
        if path == "/api/watch" and method == "GET":
            u, pl = self.need_module("comando")
            try:
                return self.send_json(200, S.watch_view(u["id"]))
            except providers.ProviderError as e:
                raise HttpError(503, str(e))
        if path == "/api/watch" and method == "POST":
            u, pl = self.need_module("comando")
            d = self.read_json()
            try:
                if d.get("sector"):
                    syms = S.sectors().get(d["sector"])
                    if not syms:
                        raise ValueError("Sector no existe")
                    n = userdata.watch_add(u["id"], syms[:userdata.MAX_WATCH])
                else:
                    n = userdata.watch_add(u["id"], [d.get("symbol")])
            except ValueError as e:
                raise HttpError(400, str(e))
            return self.send_json(201, {"added": n})
        m = re.fullmatch(r"/api/watch/([A-Za-z.\-]{1,6})", path)
        if m and method == "DELETE":
            u, pl = self.need_module("comando")
            userdata.watch_remove(u["id"], m.group(1))
            return self.send_json(200, {"ok": True})

        # ---- Listas Optionsbb (poco / moderado / alto riesgo) ----
        if path == "/api/lists" and method == "GET":
            u, pl = self.need_module("listas")
            return self.send_json(200, S.lists_info(u["id"]))
        if path == "/api/lists/view" and method == "GET":
            u, pl = self.need_module("listas")
            try:
                return self.send_json(200, S.list_view(u["id"], q1("risk"), q1("src", "optionsbb")))
            except ValueError as e:
                raise HttpError(400, str(e))
            except providers.ProviderError as e:
                raise HttpError(503, str(e))
        m = re.fullmatch(r"/api/lists/(low|mid|high)", path)
        if m and method == "POST":
            u, pl = self.need_module("listas")
            try:
                return self.send_json(200, {"symbols": userdata.set_my_list(u["id"], m.group(1), self.read_json().get("symbols"))})
            except ValueError as e:
                raise HttpError(400, str(e))
        # ---- v3.0: calculadora / earnings / dividendos / GEX ----
        def sym_arg():
            sy = q1("symbol").strip().upper()
            if not service.SYM_RE.match(sy):
                raise HttpError(400, "Símbolo no válido")
            return sy

        try:
            if path == "/api/opcalc" and method == "POST":
                u, pl = self.need_module("opciones")
                return self.send_json(200, S.opcalc(self.read_json(), pl))
            if path == "/api/earnings" and method == "GET":
                self.need_module("earnings")
                return self.send_json(200, S.earnings_view(sym_arg()))
            if path == "/api/dividends" and method == "GET":
                u, pl = self.need_module("dividendos")
                return self.send_json(200, S.dividends_view(sym_arg(), plans.at_least(pl, "intermedio")))
            if path == "/api/dividends/table" and method == "GET":
                u, pl = self.need_module("dividendos")
                syms = [x for x in q1("symbols").upper().split(",") if service.SYM_RE.match(x)][:20]
                rows = []
                for sy in syms:
                    try:
                        rows.append(S.dividends_view(sy, False))
                    except providers.ProviderError:
                        pass
                return self.send_json(200, {"rows": rows})
            if path == "/api/gex" and method == "GET":
                self.need_module("gex")
                return self.send_json(200, S.gex_view(sym_arg(), q1("expiry") or None))
        except (optcalc.CalcError, ValueError, TypeError) as e:
            raise HttpError(400, str(e))
        except providers.ProviderError as e:
            raise HttpError(503, str(e))

        if path == "/api/guide" and method == "GET":
            self.need_access()
            g = guide.get()
            qs_ = S.quotes_for(g["examples"])
            g["quotes"] = [{"symbol": s_, "price": (qs_.get(s_) or {}).get("price")} for s_ in g["examples"]]
            return self.send_json(200, g)
        if path == "/api/admin/guide" and method == "POST":
            self.need_admin()
            try:
                return self.send_json(200, guide.set_(self.read_json()))
            except ValueError as e:
                raise HttpError(400, str(e))
        if path == "/api/admin/default-lists" and method == "POST":
            self.need_admin()
            try:
                return self.send_json(200, {"lists": userdata.set_default_lists(self.read_json())})
            except ValueError as e:
                raise HttpError(400, str(e))

        # ---- Mi ETF ----
        def num(name, default, lo, hi):
            try:
                v = float(q1(name, str(default)))
            except ValueError:
                raise HttpError(400, f"{name} no válido")
            if not lo <= v <= hi:
                raise HttpError(400, f"{name} fuera de rango")
            return v
        if path == "/api/etfs" and method == "GET":
            u, pl = self.need_module("etf")
            return self.send_json(200, {"etfs": userdata.etfs(u["id"]), "max": userdata.MAX_ETF_POS})
        if path == "/api/etfs" and method == "POST":
            u, pl = self.need_module("etf")
            try:
                eid = userdata.etf_create(u["id"], self.read_json().get("name"))
            except ValueError as e:
                raise HttpError(400, str(e))
            return self.send_json(201, {"id": eid})
        if path == "/api/etfs/official" and method == "GET":
            u, pl = self.need_module("etf")
            try:
                return self.send_json(200, {"etfs": S.official_list()})
            except providers.ProviderError as e:
                raise HttpError(503, str(e))
        m = re.fullmatch(r"/api/etfs/official/(low|mid|high)/view", path)
        if m and method == "GET":
            u, pl = self.need_module("etf")
            try:
                return self.send_json(200, S.official_view(m.group(1), num("amount", 0, 0, 100_000_000), int(num("days", 90, 20, 360)), num("otm", 5, 0, 50) / 100, (num("iv", 0, 0, 300) / 100) or None))
            except ValueError as e:
                raise HttpError(400, str(e))
            except providers.ProviderError as e:
                raise HttpError(503, str(e))
        if path == "/api/admin/official-etfs" and method == "POST":
            self.need_admin()
            try:
                userdata.set_official_etfs(self.read_json())
            except ValueError as e:
                raise HttpError(400, str(e))
            return self.send_json(200, {"etfs": S.official_list()})
        m = re.fullmatch(r"/api/etfs/(\d+)", path)
        if m and method == "PUT":
            u, pl = self.need_module("etf")
            d = self.read_json()
            try:
                pos = S.resolve_positions(d.get("positions", []))
                userdata.etf_save(u["id"], int(m.group(1)), d.get("name"), pos)
            except ValueError as e:
                raise HttpError(400, str(e))
            except providers.ProviderError as e:
                raise HttpError(503, str(e))
            return self.send_json(200, {"positions": pos})
        if m and method == "DELETE":
            u, pl = self.need_module("etf")
            userdata.etf_delete(u["id"], int(m.group(1)))
            return self.send_json(200, {"ok": True})
        m = re.fullmatch(r"/api/etfs/(\d+)/view", path)
        if m and method == "GET":
            u, pl = self.need_module("etf")
            days = int(num("days", 90, 20, 360))
            try:
                return self.send_json(200, S.etf_view(u["id"], int(m.group(1)), days, num("otm", 5, 0, 50) / 100, (num("iv", 0, 0, 300) / 100) or None))
            except ValueError as e:
                raise HttpError(400, str(e))
            except providers.ProviderError as e:
                raise HttpError(503, str(e))

        # ---- referidos ----
        if path == "/api/referrals" and method == "GET":
            u, _pl = self.need_module("referidos")
            return self.send_json(200, referrals.overview(u["id"]))
        if path == "/api/referrals/claim" and method == "POST":
            u = self.need_user()
            try:
                referrals.claim(u["id"], self.read_json().get("code"))
            except ValueError as e:
                raise HttpError(400, str(e))
            return self.send_json(200, {"ok": True})
        if path == "/api/admin/referrals" and method == "GET":
            self.need_admin()
            return self.send_json(200, referrals.admin_overview())
        if path == "/api/admin/referrals/rules" and method == "POST":
            self.need_admin()
            try:
                return self.send_json(200, {"rules": referrals.set_rules(self.read_json())})
            except ValueError as e:
                raise HttpError(400, str(e))
        if path == "/api/admin/referrals/qualify" and method == "POST":
            self.need_admin()
            try:
                uid_ = int(self.read_json().get("user_id"))
            except (TypeError, ValueError):
                raise HttpError(400, "Usuario no válido")
            res = referrals.qualify(uid_)
            if res is None:
                raise HttpError(400, "Ese usuario no tiene un referido pendiente")
            return self.send_json(200, res)
        m = re.fullmatch(r"/api/admin/referrals/reward/(\d+)/done", path)
        if m and method == "POST":
            self.need_admin()
            referrals.mark_done(int(m.group(1)))
            return self.send_json(200, {"ok": True})

        # ---- ¿Qué hubiera pasado si…? y Apalancados + Cover Call ----
        if path == "/api/whatif/examples" and method == "GET":
            u, _pl = self.need_module("escenarios")
            mine = [dict(c, kind="mine", category="Mis casos") for c in userdata.pref_get(u["id"], "whatif_cases", [])]
            return self.send_json(200, {"examples": scenarios.all_official(), "mine": mine})
        if path == "/api/whatif/cases" and method == "POST":
            u, _pl = self.need_module("escenarios")
            try:
                c = scenarios.clean_case(self.read_json())
            except ValueError as e:
                raise HttpError(400, str(e))
            lst = userdata.pref_get(u["id"], "whatif_cases", [])
            if len(lst) >= 20:
                raise HttpError(400, "Puedes guardar hasta 20 casos. Elimina alguno para guardar otro.")
            c["id"] = "u" + secrets.token_hex(4)
            userdata.pref_set(u["id"], "whatif_cases", lst + [c])
            return self.send_json(201, {"case": dict(c, kind="mine", category="Mis casos")})
        m = re.fullmatch(r"/api/whatif/cases/(u[0-9a-f]+)", path)
        if m and method == "DELETE":
            u, _pl = self.need_module("escenarios")
            lst = userdata.pref_get(u["id"], "whatif_cases", [])
            userdata.pref_set(u["id"], "whatif_cases", [c for c in lst if c.get("id") != m.group(1)])
            return self.send_json(200, {"ok": True})
        if path == "/api/admin/whatif/cases" and method == "POST":
            self.need_admin()
            try:
                c = scenarios.clean_case(self.read_json())
            except ValueError as e:
                raise HttpError(400, str(e))
            c["id"] = "a" + secrets.token_hex(4)
            scenarios.save_admin_cases(scenarios.admin_cases() + [c])
            return self.send_json(201, {"case": dict(c, kind="admin")})
        m = re.fullmatch(r"/api/admin/whatif/cases/(a[0-9a-f]+)", path)
        if m and method == "DELETE":
            self.need_admin()
            scenarios.save_admin_cases([c for c in scenarios.admin_cases() if c.get("id") != m.group(1)])
            return self.send_json(200, {"ok": True})
        if path == "/api/whatif" and method == "POST":
            self.need_module("escenarios")
            d = self.read_json()
            try:
                shares, otm = float(d.get("shares")), float(d.get("otm", 5)) / 100
                iv = float(d.get("iv") or 0) / 100 or None
                if d.get("prices"):
                    prices = [float(x) for x in d["prices"]]
                    if len(prices) > 61:
                        raise ValueError("Máximo 60 meses")
                    r = overlay.run_cycles(prices, [iv or 0.35] * (len(prices) - 1), otm, shares)
                    r["vol"] = iv or 0.35
                else:
                    sym = str(d.get("symbol") or "").upper()
                    if not SYM_RE.match(sym):
                        raise ValueError("Símbolo no válido")
                    r = S.overlay_symbol(sym, shares, int(min(360, max(20, float(d.get("days", 360))))), otm, iv)
            except (TypeError, ValueError) as e:
                raise HttpError(400, str(e) if str(e) else "Datos no válidos")
            except providers.ProviderError as e:
                raise HttpError(503, str(e))
            return self.send_json(200, r)
        if path == "/api/lev" and method == "GET":
            self.need_module("apalancados")
            syms = [x["symbol"] for x in scenarios.LEVERAGED]
            try:
                qs = S.quotes_for(syms)
            except providers.ProviderError as e:
                raise HttpError(503, str(e))
            return self.send_json(200, {"items": [{**x, "price": (qs.get(x["symbol"]) or {}).get("price"), "change_pct": (qs.get(x["symbol"]) or {}).get("change_pct")} for x in scenarios.LEVERAGED]})

        # ---- Análisis de acción y ranking ----
        def rank_keys(pl):
            keys = set(plans.allowed_strategy_ids(pl))
            if pl == "avanzado":
                keys |= {f"cat:{c['id']}" for c in library.list_catalog()}
            return keys
        if path == "/api/analysis" and method == "GET":
            u, pl = self.need_module("analisis")
            sym = q1("symbol").upper()
            if not SYM_RE.match(sym):
                raise HttpError(400, "Símbolo no válido")
            try:
                return self.send_json(200, S.analysis(sym, rank_keys(pl)))
            except providers.ProviderError as e:
                raise HttpError(503, f"No pude obtener datos de {sym}: {e}")
        if path == "/api/rank" and method == "GET":
            u, pl = self.need_module("ranking")
            tf = q1("tf", "15m")
            if tf not in analytics.TF_KEYS:
                raise HttpError(400, "Temporalidad no válida")
            return self.send_json(200, S.ranking_view(tf, rank_keys(pl)))
        if path == "/api/picks" and method == "POST":
            u, pl = self.need_module("senales")
            d = self.read_json()
            try:
                userdata.pick_set(u["id"], pl, d.get("kind"), d.get("ref"), bool(d.get("on")))
            except ValueError as e:
                raise HttpError(400, str(e))
            return self.send_json(200, {"ok": True})

        # ---- 401(k) ----
        if path.startswith("/api/k401/"):
            u, pl = self.need_module("k401")
            try:
                if path == "/api/k401/project" and method == "POST":
                    return self.send_json(200, k401.project(self.read_json()))
                if path == "/api/k401/goal" and method == "POST":
                    return self.send_json(200, k401.goal(self.read_json()))
                if path == "/api/k401/fees" and method == "POST":
                    return self.send_json(200, k401.fees(self.read_json()))
                if path == "/api/k401/holdings" and method == "GET":
                    hs = userdata.holdings(u["id"])
                    qs = S.quotes_for([h["symbol"] for h in hs]) if hs else {}
                    rows = [{**h, "price": (qs.get(h["symbol"]) or {}).get("price"), "change_pct": (qs.get(h["symbol"]) or {}).get("change_pct")} for h in hs]
                    return self.send_json(200, {"rows": rows, "limits": k401.LIMITS_2026, "max": userdata.MAX_HOLD})
                if path == "/api/k401/holdings" and method == "POST":
                    d = self.read_json()
                    userdata.holding_set(u["id"], d.get("symbol"), d.get("shares"), d.get("cost"))
                    return self.send_json(201, {"ok": True})
                m = re.fullmatch(r"/api/k401/holdings/([A-Za-z.\-]{1,6})", path)
                if m and method == "DELETE":
                    userdata.holding_remove(u["id"], m.group(1))
                    return self.send_json(200, {"ok": True})
            except (k401.KError, ValueError) as e:
                raise HttpError(400, str(e))
            except providers.ProviderError as e:
                raise HttpError(503, str(e))

        # ---- administración ----
        if path == "/api/admin/report" and method == "POST":
            self.need_admin()
            fname = urllib.parse.unquote(self.headers.get("X-Filename", "reporte.csv"))[:150]
            sym = (self.headers.get("X-Symbol") or "").strip().upper()
            if sym and not SYM_RE.match(sym):
                raise HttpError(400, "Símbolo no válido")
            try:
                parsed = reports.parse(fname, self.read_body(10_000_000))
            except reports.ReportError as e:
                raise HttpError(400, str(e))
            rid = reports.save_report(fname, sym or parsed["symbol"], parsed["trades"], parsed["period_start"], parsed["period_end"])
            return self.send_json(201, {"id": rid, "trades": len(parsed["trades"]), "warnings": parsed["warnings"]})
        if path == "/api/admin/users" and method == "GET":
            self.need_admin()
            return self.send_json(200, {"users": [auth.public_user(u) for u in db.q("SELECT * FROM users ORDER BY id DESC LIMIT 500")]})
        m = re.fullmatch(r"/api/admin/users/(\d+)", path)
        if m and method == "POST":
            self.need_admin()
            d = self.read_json()
            try:
                u = auth.admin_update(int(m.group(1)), d.get("action", ""), d.get("value"))
            except (ValueError, TypeError) as e:
                raise HttpError(400, str(e))
            return self.send_json(200, {"user": auth.public_user(u)})
        if path == "/api/admin/sector" and method in ("POST", "DELETE"):
            self.need_admin()
            d = self.read_json()
            try:
                if method == "POST":
                    service.sector_add(d.get("sector"), d.get("symbol"))
                else:
                    service.sector_remove(d.get("sector") or "", d.get("symbol"))
            except ValueError as e:
                raise HttpError(400, str(e))
            return self.send_json(200, {"ok": True})
        if path == "/api/admin/watchlist" and method == "POST":
            self.need_admin()
            try:
                wl = service.parse_watchlist(self.read_body(2_000_000))
            except Exception as e:
                raise HttpError(400, f"No se pudo leer el Excel: {e}")
            service.save_watchlist(wl)
            S.updated.update({"quotes": 0, "scan": 0, "chains": 0})
            return self.send_json(200, {"sectors": len(wl), "symbols": len(S.symbols())})
        if path == "/api/admin/snapshot" and method == "POST":
            self.need_admin()
            kind = self.read_json().get("kind")
            if kind not in ("CLOSE", "MORNING"):
                raise HttpError(400, "kind debe ser CLOSE o MORNING")
            try:
                return self.send_json(200, {"rows": S.run_snapshot(kind)})
            except providers.ProviderError as e:
                raise HttpError(503, str(e))
        if path == "/api/admin/schwab/login" and method == "GET":
            self.need_admin()
            try:
                return self.send_json(200, {"url": providers.SchwabProvider().auth_url(), "callback": config.SCHWAB_CALLBACK})
            except providers.ProviderError as e:
                raise HttpError(400, str(e))
        if path == "/api/admin/schwab/exchange" and method == "POST":
            self.need_admin()
            try:
                providers.SchwabProvider().exchange_code(self.read_json().get("url", ""))
            except providers.ProviderError as e:
                raise HttpError(400, str(e))
            S.updated.update({"quotes": 0, "scan": 0, "chains": 0})
            return self.send_json(200, {"ok": True, "schwab": providers.SchwabProvider().status()})
        if path == "/api/health":
            return self.send_json(200, {"ok": True})
        raise HttpError(404, "Ruta no encontrada")


# ---------------------------------------------------------------- arranque / CLI
def bootstrap():
    db.conn()
    if not db.q1("SELECT 1 FROM watchlist LIMIT 1") and not db.kv_get("sectors_seeded"):
        service.save_watchlist(service.DEFAULT_SECTORS)
        db.kv_set("sectors_seeded", "1")
    library.seed_catalog()
    if providers.get_provider().name == "demo":
        reports.seed_demo()


def main(argv):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if len(argv) > 1:
        cmd = argv[1]
        db.conn()
        if cmd == "create-admin":
            email = argv[2] if len(argv) > 2 else input("Correo del administrador: ")
            pw = argv[3] if len(argv) > 3 else getpass.getpass("Contraseña (mín. 8): ")
            try:
                u = auth.create_user(email, pw, "Admin", role="admin")
                print("Administrador creado:", u["email"])
            except ValueError as e:
                existing = auth.get_user_by_email(email)
                if existing and "registrado" in str(e):
                    db.x("UPDATE users SET role='admin' WHERE id=?", (existing["id"],))
                    print("El usuario ya existía: ahora es administrador.")
                else:
                    sys.exit(f"Error: {e}")
            return
        if cmd == "import-watchlist" and len(argv) > 2:
            wl = service.parse_watchlist(argv[2])
            service.save_watchlist(wl)
            print(f"{len(wl)} sectores, {sum(len(v) for v in wl.values())} acciones")
            return
        if cmd == "schwab-login":
            sp = providers.SchwabProvider()
            print("1) Abre esta URL, inicia sesión y autoriza la app:\n\n", sp.auth_url(), "\n")
            print("2) Tu navegador terminará en una página que no carga (https://127.0.0.1...). Copia la URL COMPLETA de esa página.")
            sp.exchange_code(input("3) Pégala aquí: "))
            print("Conectado:", sp.status())
            return
        sys.exit(__doc__)
    bootstrap()
    service.SERVICE.start()
    srv = ThreadingHTTPServer((config.HOST, config.PORT), Handler)
    srv.daemon_threads = True
    mode = providers.get_provider().name.upper()
    print(f"OPTIONS BB · Centro de Comando  →  http://{config.HOST}:{config.PORT}   (datos: {mode})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.SERVICE.stop()


if __name__ == "__main__":
    main(sys.argv)
