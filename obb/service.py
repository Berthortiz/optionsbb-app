"""Servicio de fondo: refresca cotizaciones, señales y cadenas de opciones, y guarda las fotos de OI."""
import io
import logging
import re
import threading
import time

from . import analytics, clock, db, events, flow, library, optcalc, overlay, plans, providers, reports, rules, strategies, userdata

log = logging.getLogger("obb")
SYM_RE = re.compile(r"^[A-Z][A-Z.\-]{0,5}$")
INDEX_EXTRA = ["SPY", "QQQ"]  # siempre disponibles para gráfico y volumen
MORNING_AT, CLOSE_AT = (9, 0), (16, 15)


# ---------------------------------------------------------------- watchlist
def parse_watchlist(source) -> dict:
    """Excel con columnas 'Sector' y una lista de símbolos separados por coma."""
    from . import xlsxlite
    out = {}
    for _name, rows in xlsxlite.sheets(source):
        for i, r in enumerate(rows):
            cells = [str(c or "").strip().lower() for c in r]
            if "sector" in cells:
                sc = cells.index("sector")
                for rr in rows[i + 1:]:
                    sector = str(rr[sc] or "").strip() if sc < len(rr) else ""
                    raw = str(rr[sc + 1] or "") if sc + 1 < len(rr) else ""
                    syms = [s.strip().upper() for s in re.split(r"[,\s;]+", raw) if s.strip()]
                    syms = [s for s in syms if SYM_RE.match(s)]
                    if sector and syms:
                        out[sector] = list(dict.fromkeys(syms))
                break
        if out:
            break
    if not out:
        raise ValueError("No encontré una tabla con la columna 'Sector' y sus acciones")
    return out


# Lista definitiva de sectores y acciones clave (se carga una sola vez; después se edita desde la app).
DEFAULT_SECTORS = {
    "Technology": ["NVDA", "AVGO", "AMD", "ANET", "PLTR"],
    "Communication Services": ["GOOGL", "META", "NFLX", "TTD", "APP"],
    "Consumer Discretionary": ["AMZN", "TSLA", "MELI", "CAVA", "DECK"],
    "Consumer Staples": ["COST", "WMT", "CELH", "MNST", "ELF"],
    "Health Care": ["LLY", "NVO", "HIMS", "VRTX", "ISRG"],
    "Financials": ["JPM", "BLK", "COIN", "HOOD", "IBKR"],
    "Industrials": ["GE", "CARR", "ETN", "PH", "HUBB"],
    "Energy": ["FANG", "CEG", "VST", "LNG", "OXY"],
    "Materials": ["FCX", "NUE", "STLD", "MP", "CRH"],
    "Real Estate": ["PLD", "CCI", "EQIX", "WELL", "VICI"],
    "Utilities": ["VST", "CEG", "NRG", "SO", "DUK"],
}


def save_watchlist(wl: dict):
    db.x("DELETE FROM watchlist")
    db.many("INSERT OR IGNORE INTO watchlist(sector,symbol) VALUES(?,?)", [(s, sym) for s, syms in wl.items() for sym in syms])


class Service:
    def __init__(self):
        self.provider = providers.get_provider()
        self.quotes, self.signals, self.chains = {}, {}, {}
        self.candles = {}
        self.top, self.vbs, self.idea = [], {}, ""
        self.updated = {"quotes": 0, "scan": 0, "chains": 0, "eff": 0}
        self.eff = None
        self._dcache, self._bcache, self._xq = {}, {}, {}
        self._y5, self._chc = {}, {}
        self.errors = {}
        self._attempts = {}
        self._chart_cache = {}
        self._stop = threading.Event()
        self._busy = threading.Lock()
        self.thread = None

    # ------------------------------------------------------------ helpers
    def sectors(self) -> dict:
        out = {}
        for r in db.q("SELECT sector,symbol FROM watchlist ORDER BY rowid"):
            out.setdefault(r["sector"], []).append(r["symbol"])
        return out

    def symbols(self) -> list:
        return list(dict.fromkeys(s for syms in self.sectors().values() for s in syms))

    def allowed_chart_symbols(self) -> set:
        return set(self.symbols()) | set(INDEX_EXTRA)

    def _sleep(self):
        if self.provider.name == "schwab":
            time.sleep(0.6)  # Schwab ≈ 120 peticiones/min

    @property
    def last_error(self) -> str:
        return " | ".join(self.errors.values())

    def _guard(self, fn, label):
        try:
            fn()
            self.errors.pop(label, None)
        except providers.ProviderError as e:
            self.errors[label] = f"{label}: {e}"
            log.warning(self.errors[label])
        except Exception as e:  # no tumbar el hilo
            self.errors[label] = f"{label}: {type(e).__name__}: {e}"
            log.exception(label)

    # ------------------------------------------------------------ datos cacheados
    def get_daily(self, sym):
        hit = self._dcache.get(sym)
        if hit and time.time() - hit[0] < 900:
            return hit[1]
        c = self.provider.history(sym, "1Y")
        if len(self._dcache) > 400:
            self._dcache.clear()
        self._dcache[sym] = (time.time(), c)
        return c

    def get_bt(self, sym):
        hit = self._bcache.get(sym)
        if hit and time.time() - hit[0] < 1800:
            return hit[1]
        c = self.provider.history(sym, "BT")
        if len(self._bcache) > 200:
            self._bcache.clear()
        self._bcache[sym] = (time.time(), c)
        return c

    def quotes_for(self, syms):
        """Cotizaciones de cualquier lista de símbolos (usa las ya cargadas y pide solo las que faltan)."""
        out, missing = {}, []
        for s in syms:
            hit = self._xq.get(s)
            if s in self.quotes:
                out[s] = self.quotes[s]
            elif hit and time.time() - hit[0] < 60:
                out[s] = hit[1]
            else:
                missing.append(s)
        if missing:
            got = self.provider.quotes(missing)
            for s, q in got.items():
                self._xq[s] = (time.time(), q)
                out[s] = q
        return out

    def refresh_eff(self):
        self.eff = analytics.compute(self.symbols(), self.get_bt, self.get_daily)
        self.updated["eff"] = time.time()

    # ------------------------------------------------------------ vistas por usuario
    def _rows(self, syms, periods):
        qs = self.quotes_for(syms) if syms else {}
        rows, now = [], time.time()
        need_hist = [p for p in periods if p != "0"]
        for sym in syms:
            q = qs.get(sym) or {}
            ch = {"0": q.get("change_pct")}
            if need_hist and q.get("price") is not None:
                try:
                    ch = analytics.period_changes(self.get_daily(sym), q["price"], q.get("change_pct"), now)
                except providers.ProviderError:
                    pass
                self._sleep()
            rows.append({"symbol": sym, "price": q.get("price"), "changes": ch})
        return rows

    def watch_view(self, uid) -> dict:
        syms = userdata.watch_symbols(uid)
        periods = userdata.pref_get(uid, "watch_periods", analytics.DEFAULT_PERIODS)
        return {"rows": self._rows(syms, periods), "periods": periods, "all_periods": [{"key": k, "label": l} for k, l in analytics.PERIODS],
                "max": userdata.MAX_WATCH, "sectors": sorted(self.sectors().keys())}

    # ---- Listas Optionsbb (3 niveles de riesgo) ----
    def lists_info(self, uid) -> dict:
        return {"risks": [{"risk": r, "title": userdata.RISK_TITLES[r]} for r in userdata.RISKS],
                "optionsbb": userdata.default_lists(), "mine": userdata.my_lists(uid), "max": userdata.MAX_LIST,
                "periods": userdata.pref_get(uid, "watch_periods", analytics.DEFAULT_PERIODS),
                "all_periods": [{"key": k, "label": l} for k, l in analytics.PERIODS]}

    def list_view(self, uid, risk, src) -> dict:
        if risk not in userdata.RISKS or src not in ("optionsbb", "mine"):
            raise ValueError("Lista no válida")
        syms = userdata.default_lists()[risk] if src == "optionsbb" else userdata.my_lists(uid)[risk]
        periods = userdata.pref_get(uid, "watch_periods", analytics.DEFAULT_PERIODS)
        return {"risk": risk, "src": src, "rows": self._rows(syms, periods), "periods": periods}

    # ---- cover call de recubrimiento sobre el historial de una acción ----
    def overlay_symbol(self, sym, shares, days, otm, iv=None):
        daily = self.get_daily(sym)
        cut = time.time() - days * 86400
        cs = [x for x in daily if x["t"] >= cut] or daily
        if len(cs) < 6:
            raise overlay.OverlayError(f"Historia insuficiente de {sym}")
        r = overlay.from_daily([x["c"] for x in cs], shares, otm, iv)
        r["days"] = days
        return r

    def _etf_perf(self, pos, days, otm, iv=None) -> dict:
        qs = self.quotes_for([p["symbol"] for p in pos]) if pos else {}
        rows, val = [], 0.0
        for p in pos:
            q = qs.get(p["symbol"]) or {}
            price = q.get("price")
            row = {"symbol": p["symbol"], "shares": p["shares"], "buy_price": p.get("buy_price"), "price": price,
                   "value": (price * p["shares"]) if price else None}
            if row["value"]:
                val += row["value"]
            try:
                o = self.overlay_symbol(p["symbol"], p["shares"], days, otm, iv)
                row.update({"start": o["start"], "stock_pnl": o["stock_pnl"], "stock_pct": o["stock_pct"], "overlay_pnl": o["overlay_pnl"],
                            "overlay_pct": o["overlay_pct"], "total_pnl": o["total_pnl"], "total_pct": o["total_pct"], "lots": o["lots"],
                            "premiums": o["premiums"], "assigned": o["assigned"], "cycles": o["n"], "vol": o["vol"],
                            "state": overlay.classify(o["stock_pct"])})
            except (overlay.OverlayError, providers.ProviderError):
                row["state"] = None
            self._sleep()
            rows.append(row)
        for r in rows:
            r["weight"] = (r["value"] / val * 100) if val and r["value"] else None

        def tot(sel):
            g = [r for r in rows if r.get("state") and sel(r)]
            cost = sum(r["start"] * r["shares"] for r in g)
            st, ov = sum(r["stock_pnl"] for r in g), sum(r["overlay_pnl"] for r in g)
            return {"n": len(g), "stock_pnl": st, "overlay_pnl": ov, "total_pnl": st + ov, "cost": cost,
                    "stock_pct": st / cost * 100 if cost else None, "total_pct": (st + ov) / cost * 100 if cost else None}
        return {"days": days, "otm": otm, "value": val, "rows": rows,
                "total": tot(lambda r: True), "flat": tot(lambda r: r["state"] == "flat"), "moving": tot(lambda r: r["state"] != "flat")}

    def etf_view(self, uid, eid, days, otm, iv=None) -> dict:
        etf = userdata.etf_get(uid, eid)
        if not etf:
            raise ValueError("ETF no existe")
        out = self._etf_perf(etf["positions"], days, otm, iv)
        out.update({"id": eid, "name": etf["name"]})
        return out

    def official_list(self) -> list:
        off = userdata.official_etfs()
        qs = self.quotes_for(sorted({p["symbol"] for e in off.values() for p in e["positions"]}))
        out = []
        for k in userdata.OFFICIAL_KEYS:
            e = off[k]
            ref = sum(((qs.get(p["symbol"]) or {}).get("price") or 0) * p["shares"] for p in e["positions"])
            out.append({"key": k, "name": e["name"], "positions": e["positions"], "ref_value": ref})
        return out

    def official_view(self, key, amount, days, otm, iv=None) -> dict:
        if key not in userdata.OFFICIAL_KEYS:
            raise ValueError("ETF no existe")
        e = userdata.official_etfs()[key]
        qs = self.quotes_for([p["symbol"] for p in e["positions"]])
        ref = sum(((qs.get(p["symbol"]) or {}).get("price") or 0) * p["shares"] for p in e["positions"])
        if ref <= 0:
            raise ValueError("No hay precios para este ETF")
        amount = amount if amount and amount > 0 else ref
        scale = amount / ref
        pos = [{"symbol": p["symbol"], "shares": round(p["shares"] * scale, 4)} for p in e["positions"]]
        out = self._etf_perf(pos, days, otm, iv)
        out.update({"key": key, "name": e["name"], "amount": amount, "ref_value": ref, "scale": scale, "base": e["positions"]})
        return out

    def resolve_positions(self, items):
        """[{symbol, shares | amount}] → [{symbol, shares, buy_price}] con el precio actual."""
        if not isinstance(items, list):
            raise ValueError("Posiciones no válidas")
        clean, seen = [], set()
        for it in items:
            sym = str((it or {}).get("symbol") or "").strip().upper()
            if not userdata.SYM_RE.match(sym):
                raise ValueError(f"Símbolo no válido: {sym or '(vacío)'}")
            if sym in seen:
                raise ValueError(f"{sym} está repetida")
            seen.add(sym)
            clean.append((sym, it))
        qs = self.quotes_for([c[0] for c in clean]) if clean else {}
        out = []
        for sym, it in clean:
            price = (qs.get(sym) or {}).get("price")
            try:
                if it.get("shares") not in (None, ""):
                    shares = float(it["shares"])
                else:
                    amount = float(it.get("amount"))
                    if not price:
                        raise ValueError(f"No hay precio de {sym} para convertir los dólares")
                    shares = amount / price
            except (TypeError, ValueError) as e:
                raise ValueError(str(e) if "precio" in str(e) else f"Indica acciones o dólares válidos para {sym}")
            if not (0 < shares <= 10_000_000):
                raise ValueError(f"Cantidad fuera de rango en {sym}")
            bp = it.get("buy_price")
            out.append({"symbol": sym, "shares": round(shares, 4), "buy_price": float(bp) if isinstance(bp, (int, float)) and bp > 0 else (round(price, 2) if price else None)})
        return out

    def analysis(self, sym, allowed_keys) -> dict:
        qs = self.quotes_for([sym])
        q = qs.get(sym) or {}
        daily = self.get_daily(sym)
        vi = None
        v = self.vbs.get(sym)
        if v:
            vi = {"call_vol": v.get("call_vol"), "put_vol": v.get("put_vol"), "pcr": v.get("pcr")}
        out = {"symbol": sym, "quote": q, "summary": analytics.summary(daily, q, time.time(), vi), "tfs": []}
        c5 = self.get_bt(sym)
        for tf, label, f in analytics.TFS:
            cs = daily if tf == "1d" else analytics.resample(c5, f)
            tr = analytics.tf_trend(cs) if len(cs) >= 21 else {"trend": None, "rsi": None}
            out["tfs"].append({"tf": tf, "label": label, **{k: tr.get(k) for k in ("trend", "rsi")},
                               "best": analytics.best_for_symbol(self.eff, sym, tf, allowed_keys)})
        return out

    def ranking_view(self, tf, allowed_keys) -> dict:
        r = analytics.ranking(self.eff, tf, allowed_keys)
        r["tf"], r["tfs"] = tf, [{"key": k, "label": l} for k, l, _ in analytics.TFS]
        r["ready"] = self.eff is not None
        r["status"] = self.status()
        return r

    # ------------------------------------------------------------ refrescos
    def refresh_quotes(self):
        syms = list(dict.fromkeys(self.symbols() + INDEX_EXTRA))
        self.quotes = self.provider.quotes(syms)
        self.updated["quotes"] = time.time()

    def refresh_scan(self):
        sig, store = {}, {}
        for sym in self.symbols():
            candles = self.provider.history(sym, "SCAN")
            store[sym] = candles
            res = strategies.scan_all(candles)
            sig[sym] = {sid: {"t": candles[i]["t"], "price": candles[i]["c"]} for sid, i in res.items() if i is not None}
            self._sleep()
        self.signals, self.candles = sig, store
        self.updated["scan"] = time.time()

    def _fetch_chains(self, symbols, as_of=None):
        out = {}
        for sym in symbols:
            out[sym] = self.provider.chain(sym, as_of) if as_of else self.provider.chain(sym)
            self._sleep()
        return out

    def refresh_chains(self):
        chains = self._fetch_chains(list(dict.fromkeys(self.symbols() + INDEX_EXTRA)))
        self.chains = chains
        self.vbs = flow.volume_by_stock(chains)
        self.top = flow.top_live(chains, 8)
        self.idea = flow.idea_of_the_day(self.vbs, self.quotes)
        self.updated["chains"] = time.time()

    def run_snapshot(self, kind: str, today=None):
        """kind: CLOSE | MORNING.  Devuelve filas guardadas."""
        today = today or clock.now_et().date().isoformat()
        chains = self._fetch_chains(list(dict.fromkeys(self.symbols() + INDEX_EXTRA)))
        n = flow.save_close(today, chains) if kind == "CLOSE" else flow.save_morning(today, chains)
        log.info("snapshot %s %s: %d contratos", kind, today, n)
        return n

    def seed_demo_history(self):
        """Solo DEMO: crea 5 días de fotos CLOSE/MORNING para que 'Flujo OI' tenga datos desde el primer arranque."""
        if self.provider.name != "demo" or db.q1("SELECT 1 FROM contract_snaps LIMIT 1"):
            return
        syms = list(dict.fromkeys(self.symbols() + INDEX_EXTRA))
        eff, _ = clock.effective_session()
        days, d = [], eff
        for _ in range(5):
            d = clock.prev_bday(d)
            days.append(d)
        for d in reversed(days):
            flow.save_close(d.isoformat(), {s: self.provider.chain(s, d) for s in syms})
            m = clock.next_bday(d)
            flow.save_morning(m.isoformat(), {s: self.provider.chain(s, m) for s in syms})
        log.info("historial demo creado")

    # ------------------------------------------------------------ bucle
    def _due(self, key, every):
        return time.time() - self.updated[key] >= every

    def _try_snapshot(self, kind, today):
        k = (kind, today)
        cnt, last = self._attempts.get(k, (0, 0))
        if cnt >= 3 or time.time() - last < 900 or flow.has_snapshot(kind, today):
            return
        self._attempts[k] = (cnt + 1, time.time())
        self._guard(lambda: self.run_snapshot(kind, today), f"snapshot {kind}")

    def tick(self):
        now = clock.now_et()
        self.provider = providers.get_provider()
        live = clock.market_state(now) == "open"
        if self._due("quotes", 60 if live else 900):
            self._guard(self.refresh_quotes, "cotizaciones")
        if self._due("scan", 180 if live else 1800):
            self._guard(self.refresh_scan, "señales")
        if self._due("chains", 600 if live else 1800):
            self._guard(self.refresh_chains, "opciones")
        if self.updated["scan"] and self._due("eff", 3600):
            self._guard(self.refresh_eff, "efectividad")
        if clock.is_bday(now.date()):
            today, hm = now.date().isoformat(), (now.hour, now.minute)
            if hm >= MORNING_AT:
                self._try_snapshot("MORNING", today)
            if hm >= CLOSE_AT:
                self._try_snapshot("CLOSE", today)

    def start(self):
        def loop():
            self._guard(self.seed_demo_history, "historial demo")
            while not self._stop.is_set():
                if self._busy.acquire(blocking=False):
                    try:
                        self.tick()
                    finally:
                        self._busy.release()
                self._stop.wait(20)

        self.thread = threading.Thread(target=loop, name="obb-service", daemon=True)
        self.thread.start()

    def stop(self):
        self._stop.set()

    # ------------------------------------------------------------ respuestas para la API
    def status(self) -> dict:
        sch = providers.SchwabProvider()
        return {"mode": self.provider.name, "market": clock.market_state(), "updated": self.updated, "error": self.last_error,
                "schwab": sch.status(), "now": time.time()}

    def rule_hits(self, rule: dict) -> list:
        """Símbolos donde la regla dio señal en las últimas velas."""
        sec_of = {}
        for sec, syms in self.sectors().items():
            for s in syms:
                sec_of.setdefault(s, sec)
        rows = []
        for sym, candles in self.candles.items():
            i = rules.find_signal(rule, candles)
            if i is None:
                continue
            q = self.quotes.get(sym) or {}
            rows.append({"symbol": sym, "price": q.get("price", candles[i]["c"]), "change_pct": q.get("change_pct"),
                         "t": candles[i]["t"], "sector": sec_of.get(sym)})
        rows.sort(key=lambda r: (r["change_pct"] or 0), reverse=(rule["side"] == "BULL"))
        return rows

    def core_hits(self, sid):
        st = strategies.BY_ID[sid]
        sec_of = {}
        for sec, syms in self.sectors().items():
            for s in syms:
                sec_of.setdefault(s, sec)
        rows = []
        for sym, sigs in self.signals.items():
            hit = sigs.get(sid)
            if hit:
                q = self.quotes.get(sym) or {}
                rows.append({"symbol": sym, "price": q.get("price", hit["price"]), "change_pct": q.get("change_pct"), "t": hit["t"], "sector": sec_of.get(sym)})
        rows.sort(key=lambda r: (r["change_pct"] or 0), reverse=(st["side"] == "BULL"))
        return rows

    def signals_view(self, uid, plan="avanzado") -> dict:
        followed = {(p["kind"], p["ref"]) for p in userdata.picks(uid)}

        def pack(item, kind):
            return {**{k: item[k] for k in ("id", "name", "side", "text")}, "hits": self.rule_hits(item["rule"]),
                    "followed": (kind, str(item["id"])) in followed, "kind": kind}
        cat = library.list_catalog()
        custom = library.list_custom(uid)
        core = []
        for sid in plans.allowed_strategy_ids(plan):
            st = strategies.BY_ID[sid]
            core.append({"id": sid, "name": st["label"], "side": st["side"], "text": [], "hits": self.core_hits(sid),
                         "followed": ("core", sid) in followed, "kind": "core"})
        out = {"catalog": [{**pack(c, "cat"), "source": c["source"], "language": c["language"], "description": c["description"]} for c in cat],
               "custom": [pack(c, "custom") for c in custom], "core": core, "status": self.status()}
        allc = {("core", c["id"]): c for c in core}
        allc.update({("cat", str(c["id"])): c for c in out["catalog"]})
        allc.update({("custom", str(c["id"])): c for c in out["custom"]})
        out["picks"] = [allc[(p["kind"], p["ref"])] for p in userdata.picks(uid) if (p["kind"], p["ref"]) in allc]
        return out

    def command(self, allowed=None) -> dict:
        sectors = self.sectors()
        sec_of = {}
        for sec, syms in sectors.items():
            for s in syms:
                sec_of.setdefault(s, sec)
        out = {"BULL": {}, "BEAR": {}}
        use = [st for st in strategies.STRATEGIES if allowed is None or st["id"] in allowed]
        locked = {"BULL": sum(1 for st in strategies.STRATEGIES if st["side"] == "BULL") - sum(1 for st in use if st["side"] == "BULL"),
                  "BEAR": sum(1 for st in strategies.STRATEGIES if st["side"] == "BEAR") - sum(1 for st in use if st["side"] == "BEAR")}
        for st in use:
            rows = []
            for sym, sigs in self.signals.items():
                hit = sigs.get(st["id"])
                if not hit:
                    continue
                q = self.quotes.get(sym) or {}
                rows.append({"symbol": sym, "strategy": st["label"], "signal": "BUY" if st["side"] == "BULL" else "SELL",
                             "price": q.get("price", hit["price"]), "change_pct": q.get("change_pct"), "t": hit["t"],
                             "sector": sec_of.get(sym)})
            rows.sort(key=lambda r: (r["change_pct"] or 0), reverse=(st["side"] == "BULL"))
            out[st["side"]][st["id"]] = rows
        return {"signals": out, "top": self.top, "idea": self.idea, "status": self.status(),
                "symbols": sorted(self.allowed_chart_symbols()),
                "strategies": [{"id": s["id"], "side": s["side"], "label": s["label"]} for s in use], "locked": locked}

    def sectors_view(self, allowed=None) -> dict:
        res = []
        for sec, syms in self.sectors().items():
            items = []
            for s in syms:
                q, v = self.quotes.get(s) or {}, self.vbs.get(s) or {}
                sigs = [{"id": sid, "side": strategies.BY_ID[sid]["side"], "label": strategies.BY_ID[sid]["label"]}
                        for sid in (self.signals.get(s) or {}) if allowed is None or sid in allowed]
                items.append({"symbol": s, "price": q.get("price"), "change_pct": q.get("change_pct"),
                              "call_vol": v.get("call_vol"), "put_vol": v.get("put_vol"), "pcr": v.get("pcr"), "signals": sigs})
            res.append({"sector": sec, "stocks": items})
        return {"sectors": res, "status": self.status()}

    def chart(self, symbol, rng, bull_ids, bear_ids) -> dict:
        if symbol not in self.allowed_chart_symbols():
            raise ValueError("Símbolo fuera de la lista")
        if rng not in ("1D", "5D", "1M", "3M", "1Y"):
            raise ValueError("Rango no válido")
        key, ttl = (symbol, rng, self.provider.name), (30 if rng in ("1D", "5D") else 300)
        hit = self._chart_cache.get(key)
        if hit and time.time() - hit[0] < ttl:
            candles = hit[1]
        else:
            candles = self.provider.history(symbol, rng)
            if len(self._chart_cache) > 300:
                self._chart_cache.clear()
            self._chart_cache[key] = (time.time(), candles)
        marks = []
        if rng in ("1D", "5D"):
            marks = strategies.all_signal_marks(candles, [i for i in (bull_ids + bear_ids)])
        q = self.quotes.get(symbol) or {}
        r4 = lambda v: None if v is None else round(v, 4)
        return {
            "symbol": symbol, "range": rng, "mode": self.provider.name,
            "candles": [{"t": c["t"], "o": r4(c["o"]), "h": r4(c["h"]), "l": r4(c["l"]), "c": r4(c["c"]), "v": c["v"]} for c in candles],
            "sma9": [r4(v) for v in strategies.sma_series(candles, 9)],
            "sma21": [r4(v) for v in strategies.sma_series(candles, 21)],
            "marks": marks,
            "quote": {"price": q.get("price"), "change": q.get("change"), "change_pct": q.get("change_pct")},
        }


    # ---- v3.0: calculadora, earnings, dividendos, GEX ----
    def get_5y(self, sym):
        hit = self._y5.get(sym)
        if hit and time.time() - hit[0] < 6 * 3600:
            return hit[1]
        c = self.provider.history(sym, "5Y")
        if len(self._y5) > 60:
            self._y5.clear()
        self._y5[sym] = (time.time(), c)
        return c

    def chain_for(self, sym):
        hit = self._chc.get(sym)
        if hit and time.time() - hit[0] < 60:
            return hit[1]
        c = self.provider.chain(sym)
        if len(self._chc) > 30:
            self._chc.clear()
        self._chc[sym] = (time.time(), c)
        return c

    def _spot(self, sym):
        q = self.quotes_for([sym]).get(sym) or {}
        if q.get("price") is None:
            raise providers.ProviderError(f"No encontré precio para {sym}")
        return q["price"]

    def opcalc(self, d, plan):
        sym = (d.get("symbol") or "").strip().upper()
        if sym and not SYM_RE.match(sym):
            raise optcalc.CalcError("Símbolo no válido")
        spot = d.get("spot")
        spot = float(spot) if spot not in (None, "") else (self._spot(sym) if sym else None)
        if not spot:
            raise optcalc.CalcError("Indica un símbolo o un precio")
        iv = float(d.get("iv") or 0.35)
        dte = int(d.get("dte") or 30)
        if d.get("legs") and plan == "avanzado":
            legs = d["legs"]
        else:
            if not d.get("template"):
                raise optcalc.CalcError("Elige una estrategia (las patas libres son del plan Avanzado)")
            legs = optcalc.template_legs(d["template"], spot, dte=dte, iv=iv)
            for g, ov in zip(legs, d.get("strikes") or []):   # el usuario puede ajustar strikes de la plantilla
                if g["type"] != "S" and ov:
                    g["strike"] = float(ov)
        res = optcalc.analyze(spot, legs, iv, days_ahead=int(d.get("days_ahead") or 0))
        res["symbol"] = sym
        return res

    def earnings_view(self, sym):
        return events.earnings(sym, self.provider, self.get_5y(sym))

    def dividends_view(self, sym, history):
        return events.dividends(sym, self.provider, self._spot(sym), history)

    def gex_view(self, sym, expiry):
        ch = self.chain_for(sym)
        out = optcalc.gex(self._spot(sym), ch, expiry)
        out["symbol"] = sym
        out["source"] = "gamma de Schwab" if any(c.get("gamma") is not None for c in ch) else "gamma calculada (Black-Scholes)"
        return out


SERVICE = Service()


def sector_add(sector: str, symbol: str):
    sector = (sector or "").strip()[:40]
    sym = (symbol or "").strip().upper()
    if not sector or not re.fullmatch(r"[A-Z0-9.\-]{1,8}", sym):
        raise ValueError("Escribe un sector y un símbolo válido")
    db.x("INSERT OR IGNORE INTO watchlist(sector,symbol) VALUES(?,?)", (sector, sym))


def sector_remove(sector: str, symbol: str | None = None):
    if symbol:
        db.x("DELETE FROM watchlist WHERE sector=? AND symbol=?", (sector, symbol.upper()))
    else:
        db.x("DELETE FROM watchlist WHERE sector=?", (sector,))
