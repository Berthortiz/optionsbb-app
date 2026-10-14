import os, sys, tempfile, threading, json, http.client, unittest, time
os.environ["OBB_DATA"] = tempfile.mkdtemp()
os.environ["OBB_DEMO"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402
from obb import analytics, auth, billing, config, covercall as cc, db, k401, library, plans, rules, service, strategies, userdata  # noqa: E402

CHAIN = """strike bid ask delta volume oi
70 4.20 4.30 .58 100 900
71 3.65 3.75 .53 200 1200
72 3.15 3.25 .48 150 800
73 2.70 2.90 .43 90 400
74 2.35 2.45 .40 80 500
75 2.08 2.15 .36 300 1500
76 1.70 1.95 .32 20 60
"""


class Client:
    def __init__(self, port):
        self.port, self.cookie = port, None

    def call(self, method, path, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        h = {"X-OBB": "1"}
        if self.cookie:
            h["Cookie"] = self.cookie
        data = None
        if body is not None:
            data = json.dumps(body); h["Content-Type"] = "application/json"
        c.request(method, path, data, h)
        r = c.getresponse(); raw = r.read()
        sc = r.getheader("Set-Cookie")
        if sc and "obb_session=" in sc:
            self.cookie = sc.split(";")[0]
        try:
            return r.status, json.loads(raw)
        except ValueError:
            return r.status, raw


class Pure(unittest.TestCase):
    def test_plans_strategy_counts(self):
        for pid, (b, r) in {"basico": (1, 1), "intermedio": (6, 6), "avanzado": (10, 10)}.items():
            ids = plans.allowed_strategy_ids(pid)
            self.assertEqual(sum(strategies.BY_ID[i]["side"] == "BULL" for i in ids), b, pid)
            self.assertEqual(sum(strategies.BY_ID[i]["side"] == "BEAR" for i in ids), r, pid)

    def test_cover_call_nflx(self):
        a1 = cc.analyze({"spot": 70.98, "chain_text": CHAIN, "sell_date": "2026-10-09", "expiry": "2026-11-06", "k": 1})["chosen"]
        a5 = cc.analyze({"spot": 70.98, "chain_text": CHAIN, "sell_date": "2026-10-09", "expiry": "2026-11-06", "k": 5})["chosen"]
        self.assertEqual((a1["strike"], a1["max_profit"], a1["breakeven"]), (71.0, 367.0, 67.33))
        self.assertEqual((a5["strike"], a5["max_profit"], a5["breakeven"]), (75.0, 610.0, 68.9))
        self.assertEqual(a5["dte"], 28)
        man = cc.analyze({"spot": 50, "strike": 55, "premium": 1.2, "dte": 30})["chosen"]
        self.assertEqual(man["max_profit"], 620.0)
        with self.assertRaises(cc.CCError): cc.analyze({"spot": 50, "strike": 55})
        with self.assertRaises(cc.CCError): cc.analyze({"spot": 50, "strike": 55, "premium": 1, "shares": 150})

    def test_wheel(self):
        cy = [{"sell_date": "2026-10-09", "expiry": "2026-11-06", "spot": 70.98, "chain_text": CHAIN, "spot_at_expiry": 76.5},
              {"sell_date": "2026-11-06", "expiry": "2026-12-04", "spot": 72.0, "chain_text": CHAIN, "spot_at_expiry": 68}]
        o = cc.simulate_wheel({"k": 1, "shares": 100}, cy)
        self.assertEqual([r["status"] for r in o["rows"]], ["ejercida", "no ejercida"])
        self.assertTrue(o["rows"][1]["rebought"]); self.assertEqual(o["rows"][0]["rebuy_gap"], 100.0)
        self.assertEqual(o["summary"]["total_pl"], 237.0); self.assertEqual(o["summary"]["assigned"], 1)
        # strike elegido por el usuario
        cy[0]["strike"] = 75
        o2 = cc.simulate_wheel({"k": 1}, cy[:1])
        self.assertEqual(o2["rows"][0]["status"], "ejercida"); self.assertEqual(o2["rows"][0]["strike"], 75)
        cy[0]["spot_at_expiry"] = None
        self.assertEqual(cc.simulate_wheel({"k": 1}, cy[:1])["rows"][0]["status"], "abierta")
        with self.assertRaises(cc.CCError): cc.simulate_wheel({"rebuy": False}, [])

    def test_rules(self):
        r = rules.validate({"side": "BULL", "conditions": [{"type": "streak", "n": 3, "color": "red"}]})
        c = [{"o": 10 - i, "c": 9 - i, "h": 10.1 - i, "l": 8.9 - i, "v": 100, "t": i} for i in range(6)]
        self.assertTrue(rules.at(r, c, 4)); self.assertIsNotNone(rules.find_signal(r, c))
        for bad in ({"side": "X", "conditions": []}, {"side": "BULL", "conditions": [{"type": "exec", "code": "1"}]},
                    {"side": "BULL", "conditions": [{"type": "sma_cross", "fast": 30, "slow": 9, "dir": "up"}]},
                    {"side": "BULL", "conditions": [{"type": "rsi", "n": 14, "op": "lt", "value": 500}]}):
            with self.assertRaises(rules.RuleError): rules.validate(bad)

    def test_video_ids(self):
        for u in ("dQw4w9WgXcQ", "https://youtu.be/dQw4w9WgXcQ?t=5", "https://www.youtube.com/watch?v=dQw4w9WgXcQ&x=1",
                  "https://www.youtube.com/shorts/dQw4w9WgXcQ", "youtube.com/embed/dQw4w9WgXcQ"):
            self.assertEqual(library.extract_id(u), "dQw4w9WgXcQ")
        for bad in ("https://evil.com/watch?v=dQw4w9WgXcQ", "javascript:alert(1)", "abc", ""):
            with self.assertRaises(library.LibError): library.extract_id(bad)
        feed = b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015"><entry><yt:videoId>dQw4w9WgXcQ</yt:videoId><title>Hola</title><published>2026-09-01T10:00:00+00:00</published></entry></feed>'
        self.assertEqual(library.parse_feed(feed)[0]["published"], "2026-09-01")

    def test_stripe_plan_mapping(self):
        u = auth.create_user("pl_p@x.com", "password1", plan="basico")
        billing.handle_event({"type": "checkout.session.completed", "data": {"object": {"customer": "cus_p", "client_reference_id": str(u["id"]), "metadata": {"plan": "intermedio"}}}})
        self.assertEqual(auth.get_user(u["id"])["plan"], "intermedio")
        config.STRIPE_PRICES["avanzado"] = "price_adv"
        billing.handle_event({"type": "customer.subscription.updated", "data": {"object": {"customer": "cus_p", "status": "active", "items": {"data": [{"price": {"id": "price_adv"}}]}}}})
        self.assertEqual(auth.get_user(u["id"])["plan"], "avanzado")


class Http(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.bootstrap()
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler); cls.srv.daemon_threads = True
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.port = cls.srv.server_address[1]
        S = service.SERVICE
        S.refresh_quotes(); S.refresh_scan(); S.refresh_chains(); S.refresh_eff()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def reg(self, email, plan):
        auth._fails.clear()
        c = Client(self.port)
        st, d = c.call("POST", "/api/auth/register", {"email": email, "password": "password1", "plan": plan})
        self.assertEqual(st, 201, d)
        return c

    def test_gating(self):
        b = self.reg("pl_b@x.com", "basico")
        st, d = b.call("GET", "/api/command"); self.assertEqual(st, 200)
        self.assertEqual(len(d["strategies"]), 2); self.assertEqual(d["locked"], {"BULL": 9, "BEAR": 9})
        self.assertEqual({s["id"] for s in d["strategies"]}, {"vela_verde", "vela_roja_apertura"})
        for p in ("/api/oi-flow", "/api/sectors", "/api/reports", "/api/signals"):
            st, d = b.call("GET", p); self.assertEqual(st, 403, p); self.assertEqual(d["reason"], "plan")
        st, d = b.call("GET", "/api/chart?symbol=SPY&range=1D&bull=vela_verde,martillo&bear=estrella_fugaz")
        self.assertEqual(st, 200); self.assertTrue(all(m["id"] == "vela_verde" for m in d["marks"]))
        self.assertEqual(b.call("POST", "/api/cc/analyze", {"spot": 50, "strike": 55, "premium": 1})[0], 200)
        i = self.reg("pl_i@x.com", "intermedio")
        st, d = i.call("GET", "/api/command"); self.assertEqual(len(d["strategies"]), 12)
        self.assertEqual(i.call("GET", "/api/oi-flow")[0], 403); self.assertEqual(i.call("GET", "/api/sectors")[0], 200)
        self.assertEqual(i.call("GET", "/api/signals")[0], 403)
        a = self.reg("pl_a@x.com", "avanzado")
        self.assertEqual(a.call("GET", "/api/oi-flow")[0], 200)
        st, d = a.call("GET", "/api/command"); self.assertEqual(len(d["strategies"]), 20)
        st, d = a.call("GET", "/api/signals"); self.assertEqual(st, 200); self.assertGreaterEqual(len(d["catalog"]), 8)
        st, d = a.call("GET", "/api/me"); self.assertEqual(d["user"]["plan"], "avanzado"); self.assertIn("senales", d["user"]["modules"])

    def test_register_bad_plan(self):
        c = Client(self.port)
        st, d = c.call("POST", "/api/auth/register", {"email": "pl_z@x.com", "password": "password1", "plan": "oro"})
        self.assertEqual(st, 400)

    def test_custom_strategies_limit(self):
        a = self.reg("pl_c2@x.com", "avanzado")
        rule = {"side": "BULL", "conditions": [{"type": "candle", "color": "green", "min_body_pct": 30}]}
        self.assertEqual(a.call("POST", "/api/custom", {"name": "Mía 1", "rule": rule})[0], 201)
        st, d = a.call("POST", "/api/custom", {"name": "Mía 2", "rule": rule}); self.assertEqual(st, 201)
        st, d = a.call("POST", "/api/custom", {"name": "Mía 3", "rule": rule}); self.assertEqual(st, 400)
        st, d = a.call("GET", "/api/signals"); self.assertEqual(len(d["custom"]), 2)
        st, d = a.call("DELETE", "/api/custom/" + str(d["custom"][0]["id"])); self.assertEqual(st, 200)
        # otro usuario no puede borrar las mías
        o = self.reg("pl_c3@x.com", "avanzado")
        left = a.call("GET", "/api/signals")[1]["custom"][0]["id"]
        o.call("DELETE", "/api/custom/%d" % left)
        self.assertEqual(len(a.call("GET", "/api/signals")[1]["custom"]), 1)
        st, d = self.reg("pl_c4@x.com", "intermedio").call("POST", "/api/custom", {"name": "x1", "rule": rule}); self.assertEqual(st, 403)

    def test_videos_lock_and_admin(self):
        adm = Client(self.port)
        auth.create_user("pl_adm@x.com", "password1", role="admin")
        self.assertEqual(adm.call("POST", "/api/auth/login", {"email": "pl_adm@x.com", "password": "password1"})[0], 200)
        st, d = adm.call("POST", "/api/admin/videos", {"url": "https://youtu.be/dQw4w9WgXcQ", "title": "Intro", "min_plan": "basico"}); self.assertEqual(st, 201, d)
        st, d = adm.call("POST", "/api/admin/videos", {"url": "https://youtu.be/aaaaaaaaaaa", "title": "Pro", "min_plan": "avanzado"}); self.assertEqual(st, 201)
        self.assertEqual(adm.call("POST", "/api/admin/videos", {"url": "https://youtu.be/aaaaaaaaaaa", "title": "dup"})[0], 400)
        b = self.reg("pl_vb@x.com", "basico")
        st, d = b.call("GET", "/api/videos"); vids = {v["title"]: v for v in d["videos"]}
        self.assertFalse(vids["Intro"]["locked"]); self.assertEqual(vids["Intro"]["yt_id"], "dQw4w9WgXcQ")
        self.assertTrue(vids["Pro"]["locked"]); self.assertNotIn("yt_id", vids["Pro"])
        self.assertEqual(b.call("POST", "/api/admin/videos", {"url": "dQw4w9WgXcQ"})[0], 403)
        st, d = adm.call("POST", "/api/admin/users/%d" % auth.get_user_by_email("pl_vb@x.com")["id"], {"action": "set_plan", "value": "avanzado"}); self.assertEqual(st, 200)
        st, d = b.call("GET", "/api/videos"); self.assertTrue(all(not v["locked"] for v in d["videos"]))

    def test_cc_api_and_sims(self):
        b = self.reg("pl_cc@x.com", "basico")
        st, d = b.call("POST", "/api/cc/chain-parse", {"text": CHAIN}); self.assertEqual(len(d["chain"]), 7)
        st, d = b.call("POST", "/api/cc/analyze", {"spot": 70.98, "chain_text": CHAIN, "expiry": "2026-11-06", "sell_date": "2026-10-09", "k": 5})
        self.assertEqual(st, 200); self.assertEqual(d["chosen"]["strike"], 75.0); self.assertTrue(any(r["recommended"] for r in d["chain"]))
        st, d = b.call("POST", "/api/cc/analyze", {"spot": -1}); self.assertEqual(st, 400)
        cycles = [{"sell_date": "2026-10-09", "expiry": "2026-11-06", "spot": 70.98, "chain_text": CHAIN, "spot_at_expiry": 76.5}]
        st, d = b.call("POST", "/api/cc/simulate", {"params": {"k": 1}, "cycles": cycles}); self.assertEqual(st, 200); self.assertEqual(d["rows"][0]["status"], "ejercida")
        st, d = b.call("POST", "/api/cc/sims", {"name": "Mi prueba", "params": {"k": 1}, "cycles": cycles}); sid = d["id"]
        self.assertEqual(len(b.call("GET", "/api/cc/sims")[1]["sims"]), 1)
        other = self.reg("pl_cc2@x.com", "basico")
        self.assertEqual(other.call("GET", "/api/cc/sims/%d" % sid)[0], 404)
        self.assertEqual(b.call("GET", "/api/cc/sims/%d" % sid)[1]["name"], "Mi prueba")
        self.assertEqual(b.call("DELETE", "/api/cc/sims/%d" % sid)[0], 200)

    def test_csp_allows_youtube(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port); c.request("GET", "/")
        r = c.getresponse(); r.read()
        csp = r.getheader("Content-Security-Policy")
        self.assertIn("frame-src https://www.youtube-nocookie.com", csp); self.assertIn("script-src 'self'", csp)

    # ---------------- nuevas funciones ----------------
    def test_watchlist(self):
        c = self.reg("pl_w@x.com", "basico")
        self.assertEqual(c.call("POST", "/api/watch", {"symbol": "nvda"})[0], 201)
        self.assertEqual(c.call("POST", "/api/watch", {"symbol": "MSFT"})[0], 201)
        self.assertEqual(c.call("POST", "/api/watch", {"symbol": "bad symbol!"})[0], 400)
        st, d = c.call("GET", "/api/watch"); self.assertEqual(st, 200)
        self.assertEqual(d["periods"], ["0"]); self.assertEqual([r["symbol"] for r in d["rows"]], ["NVDA", "MSFT"])
        self.assertIsNotNone(d["rows"][0]["changes"]["0"])
        self.assertEqual(c.call("POST", "/api/prefs", {"key": "watch_periods", "value": ["0", "7", "30", "360"]})[0], 200)
        st, d = c.call("GET", "/api/watch"); self.assertEqual(d["periods"], ["0", "7", "30", "360"])
        ch = d["rows"][0]["changes"]; self.assertTrue(all(ch[k] is not None for k in ("0", "7", "30", "360")))
        self.assertEqual(c.call("POST", "/api/prefs", {"key": "watch_periods", "value": ["999"]})[0], 400)
        self.assertEqual(c.call("POST", "/api/prefs", {"key": "watch_periods", "value": []})[0], 400)
        self.assertEqual(c.call("DELETE", "/api/watch/NVDA")[0], 200)
        self.assertEqual(len(c.call("GET", "/api/watch")[1]["rows"]), 1)
        sector = c.call("GET", "/api/watch")[1]["sectors"][0]
        self.assertEqual(c.call("POST", "/api/watch", {"sector": sector})[0], 201)
        other = self.reg("pl_w2@x.com", "basico")  # cada usuario ve solo lo suyo
        self.assertEqual(other.call("GET", "/api/watch")[1]["rows"], [])

    def test_period_changes(self):
        now = 1_000_000_000.0
        daily = [{"t": now - i * 86400, "c": 100 + (50 - i)} for i in range(50, -1, -1)]  # sube 1 por día
        r = analytics.period_changes(daily, 150, 1.5, now)
        self.assertEqual(r["0"], 1.5); self.assertAlmostEqual(r["7"], (150 / 143 - 1) * 100, 4); self.assertIsNone(r["360"])

    def test_resample(self):
        from obb import clock
        d = clock.last_bday(clock.now_et().date())
        bars = [{"t": clock.bar_epoch(d, k), "o": 10 + k, "h": 11 + k, "l": 9 + k, "c": 10.5 + k, "v": 100} for k in range(12)]
        r = analytics.resample(bars, 6)
        self.assertEqual(len(r), 2); self.assertEqual(r[0]["o"], 10); self.assertEqual(r[0]["c"], 15.5); self.assertEqual(r[0]["v"], 600)

    def test_backtest_no_lookahead_and_dedupe(self):
        c = [{"t": i, "o": 10, "h": 10, "l": 10, "c": 10 + i, "v": 1} for i in range(40)]
        res = analytics.backtest(c, lambda cs, i: True, "BULL", horizon=5)
        self.assertTrue(all(r > 0 for r in res)); self.assertEqual(len(res), 7)  # sin traslapes
        self.assertTrue(all(r < 0 for r in analytics.backtest(c, lambda cs, i: True, "BEAR", horizon=5)))

    def test_ranking_and_gating(self):
        b = self.reg("pl_r1@x.com", "basico"); self.assertEqual(b.call("GET", "/api/rank?tf=15m")[0], 403)
        a = self.reg("pl_r2@x.com", "avanzado")
        st, d = a.call("GET", "/api/rank?tf=15m"); self.assertEqual(st, 200); self.assertTrue(d["ready"])
        self.assertTrue(len(d["rows"]) + len(d["few"]) >= 20)
        avgs = [r["avg"] for r in d["rows"]]; self.assertEqual(avgs, sorted(avgs, reverse=True))
        self.assertEqual(a.call("GET", "/api/rank?tf=2h")[0], 400)
        i = self.reg("pl_r3@x.com", "intermedio"); st, d = i.call("GET", "/api/rank?tf=1d")
        self.assertTrue(all(not r["key"].startswith("cat:") for r in d["rows"] + d["few"]))
        self.assertTrue(len(d["rows"] + d["few"]) <= 12)

    def test_analysis(self):
        b = self.reg("pl_an@x.com", "basico")
        st, d = b.call("GET", "/api/analysis?symbol=AAPL"); self.assertEqual(st, 200, d)
        self.assertEqual([t["tf"] for t in d["tfs"]], ["5m", "15m", "30m", "1h", "1d"])
        s = d["summary"]; self.assertTrue(s["hi52"] >= s["lo52"]); self.assertIn("360", s["changes"])
        self.assertEqual(b.call("GET", "/api/analysis?symbol=1bad")[0], 400)

    def test_picks(self):
        a = self.reg("pl_pk@x.com", "avanzado")
        st, d = a.call("GET", "/api/signals"); cat_id = d["catalog"][0]["id"]
        self.assertEqual(a.call("POST", "/api/picks", {"kind": "cat", "ref": cat_id, "on": True})[0], 200)
        self.assertEqual(a.call("POST", "/api/picks", {"kind": "core", "ref": "martillo", "on": True})[0], 200)
        self.assertEqual(a.call("POST", "/api/picks", {"kind": "cat", "ref": 99999, "on": True})[0], 400)
        self.assertEqual(a.call("POST", "/api/picks", {"kind": "custom", "ref": 1, "on": True})[0], 400)  # no es suya
        st, d = a.call("GET", "/api/signals"); self.assertEqual(len(d["picks"]), 2); self.assertTrue(d["catalog"][0]["followed"])
        a.call("POST", "/api/picks", {"kind": "cat", "ref": cat_id, "on": False})
        self.assertEqual(len(a.call("GET", "/api/signals")[1]["picks"]), 1)

    def test_prefs_profile(self):
        c = self.reg("pl_pf@x.com", "basico")
        st, d = c.call("GET", "/api/prefs"); self.assertIsNone(d["profile"]); self.assertEqual(len(d["quiz"]), 4)
        self.assertEqual(c.call("POST", "/api/prefs", {"answers": [0, 0, 1, 0]})[1]["value"], "conservador")
        self.assertEqual(c.call("POST", "/api/prefs", {"answers": [3, 3, 3, 3]})[1]["value"], "activo")
        self.assertEqual(c.call("POST", "/api/prefs", {"answers": [1, 2]})[0], 400)
        st, d = c.call("GET", "/api/prefs"); self.assertEqual(d["profile"], "activo")
        self.assertIn("senales", d["profiles"]["activo"]["locked"]); self.assertNotIn("senales", d["profiles"]["activo"]["route"])
        self.assertEqual(c.call("POST", "/api/prefs", {"key": "evil", "value": 1})[0], 400)

    def test_k401(self):
        r = k401.project({"balance": 20000, "monthly": 500, "years": 25, "salary": 60000, "match_rate": 50, "match_cap": 6})
        self.assertEqual(r["inputs"]["employer_monthly"], 150.0)  # 50% de min(500, 6%·5000=300)
        sc = r["scenarios"]; self.assertTrue(sc["cash"]["final"] < sc["stocks"]["final"])
        self.assertTrue(sc["cash"]["final_real"] < sc["cash"]["final"]); self.assertAlmostEqual(r["cash_power_lost"], 1 - 1 / 1.03 ** 25, 3)
        self.assertEqual(len(r["rows"]), 25)
        z = k401.project({"balance": 0, "monthly": 0, "years": 5, "stock_return": 0, "fee": 0, "inflation": 0, "cash_rate": 0})
        self.assertEqual(z["scenarios"]["stocks"]["final"], 0)
        w = k401.project({"monthly": 3000, "years": 3}); self.assertTrue(w["warnings"])
        g = k401.goal({"income": 3000, "years": 25, "balance": 20000}); self.assertTrue(g["scenarios"]["cash"]["monthly"] > g["scenarios"]["stocks"]["monthly"] > 0)
        f = k401.fees({"balance": 20000, "monthly": 500, "years": 25}); self.assertTrue(f["lost"] > 0 and f["high"]["final"] < f["low"]["final"])
        for bad in ({"years": 0}, {"years": "x"}, {"monthly": -5, "years": 3}, {"inflation": 99, "years": 3}):
            with self.assertRaises(k401.KError): k401.project(bad)

    def test_k401_api_and_holdings(self):
        c = self.reg("pl_k@x.com", "basico")
        self.assertEqual(c.call("POST", "/api/k401/project", {"balance": 1000, "monthly": 100, "years": 10})[0], 200)
        self.assertEqual(c.call("POST", "/api/k401/project", {"years": 500})[0], 400)
        self.assertEqual(c.call("POST", "/api/k401/holdings", {"symbol": "AAPL", "shares": 10, "cost": 150})[0], 201)
        self.assertEqual(c.call("POST", "/api/k401/holdings", {"symbol": "AAPL", "shares": 20, "cost": 140})[0], 201)  # actualiza
        self.assertEqual(c.call("POST", "/api/k401/holdings", {"symbol": "AAPL", "shares": -1, "cost": 1})[0], 400)
        st, d = c.call("GET", "/api/k401/holdings"); self.assertEqual(len(d["rows"]), 1); self.assertEqual(d["rows"][0]["shares"], 20)
        self.assertIsNotNone(d["rows"][0]["price"]); self.assertEqual(d["limits"]["employee_401k"], 24500)
        self.assertEqual(self.reg("pl_k2@x.com", "basico").call("GET", "/api/k401/holdings")[1]["rows"], [])
        self.assertEqual(c.call("DELETE", "/api/k401/holdings/AAPL")[0], 200)


    # ------------------------------------------------------------ v2.0
    def test_v2_overlay_math(self):
        from obb import overlay
        r = overlay.run_cycles([7, 5.9, 5.1], [1.2, 1.2], 0.1, 1000)
        self.assertEqual(r["lots"], 10); self.assertAlmostEqual(r["stock_pnl"], -1900.0)
        self.assertGreater(r["premiums"], 0); self.assertAlmostEqual(r["total_pnl"], r["stock_pnl"] + r["overlay_pnl"])
        self.assertTrue(0 < r["absorbed_pct"] <= 100)
        small = overlay.run_cycles([50, 51], [0.3], 0.05, 99)           # < 100 acciones: no se puede vender call
        self.assertEqual((small["lots"], small["overlay_pnl"]), (0, 0))
        up = overlay.run_cycles([100, 130], [0.3], 0.05, 100)            # sube mucho: te ejercen y el call cuesta
        self.assertTrue(up["cycles"][0]["assigned"]); self.assertLess(up["cycles"][0]["overlay"], 0)
        with self.assertRaises(overlay.OverlayError): overlay.run_cycles([100], [], 0.05, 100)
        with self.assertRaises(overlay.OverlayError): overlay.run_cycles([100, -1], [0.3], 0.05, 100)
        self.assertEqual(overlay.classify(2), "flat"); self.assertEqual(overlay.classify(-9), "down")

    def test_v2_lists(self):
        c = self.reg("v2_l@x.com", "basico")
        st, d = c.call("GET", "/api/lists"); self.assertEqual(st, 200)
        self.assertEqual([len(d["optionsbb"][k]) for k in ("low", "mid", "high")], [10, 10, 10]); self.assertEqual(d["mine"]["low"], [])
        st, v = c.call("GET", "/api/lists/view?risk=low&src=optionsbb"); self.assertEqual(st, 200); self.assertEqual(len(v["rows"]), 10)
        self.assertEqual(c.call("GET", "/api/lists/view?risk=zzz&src=mine")[0], 400)
        st, d = c.call("POST", "/api/lists/high", {"symbols": ["nvda", "AMD", "nvda"]}); self.assertEqual((st, d["symbols"]), (200, ["NVDA", "AMD"]))
        st, v = c.call("GET", "/api/lists/view?risk=high&src=mine"); self.assertEqual([r["symbol"] for r in v["rows"]], ["NVDA", "AMD"])
        self.assertEqual(c.call("POST", "/api/lists/high", {"symbols": ["A%"]})[0], 400)
        self.assertEqual(c.call("POST", "/api/lists/high", {"symbols": [chr(65 + i) * 2 for i in range(11)]})[0], 400)
        self.assertEqual(c.call("POST", "/api/admin/default-lists", {"low": ["KO"]})[0], 403)

    def test_v2_admin_default_lists(self):
        self.assertEqual(userdata.set_default_lists({"low": ["ko"]})["low"], ["KO"])
        self.assertEqual(userdata.default_lists()["low"], ["KO"]); self.assertEqual(len(userdata.default_lists()["mid"]), 10)
        db.kv_set("default_lists", "")

    def test_v2_etf(self):
        c = self.reg("v2_e@x.com", "basico")
        st, d = c.call("POST", "/api/etfs", {"name": "Prueba"}); self.assertEqual(st, 201); eid = d["id"]
        pos = [{"symbol": "MSFT", "shares": 100}, {"symbol": "KO", "amount": 5000}, {"symbol": "AAPL", "shares": 250}]
        st, d = c.call("PUT", f"/api/etfs/{eid}", {"name": "Prueba", "positions": pos}); self.assertEqual(st, 200, d)
        ko = [p for p in d["positions"] if p["symbol"] == "KO"][0]; self.assertGreater(ko["shares"], 0); self.assertAlmostEqual(ko["shares"] * ko["buy_price"], 5000, delta=5)
        st, v = c.call("GET", f"/api/etfs/{eid}/view?days=90&otm=5"); self.assertEqual(st, 200, v)
        self.assertAlmostEqual(sum(r["weight"] for r in v["rows"]), 100, places=4)
        t = v["total"]; self.assertAlmostEqual(t["total_pnl"], t["stock_pnl"] + t["overlay_pnl"], places=4)
        self.assertAlmostEqual(v["flat"]["total_pnl"] + v["moving"]["total_pnl"], t["total_pnl"], places=4)
        ko_row = [r for r in v["rows"] if r["symbol"] == "KO"][0]
        if ko_row["lots"] == 0: self.assertEqual(ko_row["overlay_pnl"], 0)
        # validaciones y aislamiento entre usuarios
        self.assertEqual(c.call("PUT", f"/api/etfs/{eid}", {"positions": [{"symbol": "MSFT", "shares": 1}, {"symbol": "MSFT", "shares": 2}]})[0], 400)
        self.assertEqual(c.call("PUT", f"/api/etfs/{eid}", {"positions": [{"symbol": "MSFT", "shares": -5}]})[0], 400)
        self.assertEqual(c.call("PUT", f"/api/etfs/{eid}", {"positions": [{"symbol": "ZZ", "shares": 0}]})[0], 400)
        o = self.reg("v2_e2@x.com", "basico")
        self.assertEqual(o.call("GET", f"/api/etfs/{eid}/view?days=90&otm=5")[0], 400)
        self.assertEqual(o.call("PUT", f"/api/etfs/{eid}", {"positions": []})[0], 400)
        self.assertEqual(c.call("GET", f"/api/etfs/{eid}/view?days=5&otm=5")[0], 400)
        self.assertEqual(c.call("DELETE", f"/api/etfs/{eid}")[0], 200)
        for i in range(5): self.assertEqual(c.call("POST", "/api/etfs", {"name": f"e{i}"})[0], 201)
        self.assertEqual(c.call("POST", "/api/etfs", {"name": "sexto"})[0], 400)

    def test_v2_put_requires_csrf_header(self):
        c = Client(self.port); self.reg("v2_csrf@x.com", "basico")
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("PUT", "/api/etfs/1", "{}", {"Content-Type": "application/json"}); r = conn.getresponse(); r.read()
        self.assertEqual(r.status, 403)

    def test_v2_whatif_and_gating(self):
        b = self.reg("v2_w@x.com", "basico")
        st, d = b.call("GET", "/api/whatif/examples"); self.assertEqual(st, 200); self.assertTrue({"BYND", "MSFT"} <= {x["symbol"] for x in d["examples"]})
        ex = d["examples"][0]
        st, r = b.call("POST", "/api/whatif", {"prices": ex["prices"], "shares": ex["shares"], "otm": ex["otm"], "iv": ex["iv"]})
        self.assertEqual(st, 200, r); self.assertLess(r["stock_pnl"], 0); self.assertGreater(r["overlay_pnl"], 0); self.assertGreater(r["total_pnl"], r["stock_pnl"])
        st, r = b.call("POST", "/api/whatif", {"symbol": "KO", "shares": 100, "otm": 5, "days": 180}); self.assertEqual(st, 200, r)
        self.assertEqual(b.call("POST", "/api/whatif", {"prices": [10, 0], "shares": 100, "otm": 5})[0], 400)
        self.assertEqual(b.call("POST", "/api/whatif", {"symbol": "KO", "shares": "x", "otm": 5})[0], 400)
        self.assertEqual(b.call("GET", "/api/lev")[0], 403)                    # apalancados: solo Avanzado
        i = self.reg("v2_wi@x.com", "intermedio"); self.assertEqual(i.call("GET", "/api/lev")[0], 403)
        a = self.reg("v2_wa@x.com", "avanzado"); st, d = a.call("GET", "/api/lev"); self.assertEqual(st, 200)
        self.assertTrue(any(x["symbol"] == "NVDL" and x["leverage"] == 2 for x in d["items"]))
        st, me = b.call("GET", "/api/me"); self.assertNotIn("flujo", me["user"]["modules"]); self.assertIn("etf", me["user"]["modules"])
        st, cfg = Client(self.port).call("GET", "/api/config"); self.assertRegex(cfg["version"], r"^\d+\.\d+\.\d+$")

    # ---------------- v2.1 / v3.0 ----------------
    def admin(self, email):
        auth.create_user(email, "password1", role="admin"); auth._fails.clear()
        c = Client(self.port); st, d = c.call("POST", "/api/auth/login", {"email": email, "password": "password1"}); self.assertEqual(st, 200, d); return c

    def test_v21_official_etfs(self):
        u = self.reg("of_u@x.com", "basico"); a = self.admin("of_adm@x.com")
        st, d = u.call("GET", "/api/etfs/official"); self.assertEqual(st, 200, d)
        keys = [e["key"] for e in d["etfs"]]; self.assertEqual(keys, ["low", "mid", "high"])
        st, v1 = u.call("GET", "/api/etfs/official/low/view?amount=10000&days=90&otm=5"); self.assertEqual(st, 200, v1)
        st, v2 = u.call("GET", "/api/etfs/official/low/view?amount=20000&days=90&otm=5"); self.assertEqual(st, 200)
        self.assertAlmostEqual(sum(r["value"] for r in v2["rows"]), 2 * sum(r["value"] for r in v1["rows"]), delta=1)   # solo escala por el monto
        self.assertEqual(u.call("POST", "/api/admin/official-etfs", {"low": {"name": "x", "positions": [{"symbol": "KO", "shares": 10}]}})[0], 403)
        st, d = a.call("POST", "/api/admin/official-etfs", {"low": {"name": "Poco riesgo", "positions": [{"symbol": "KO", "shares": 10}, {"symbol": "PG", "shares": 5}]}}); self.assertEqual(st, 200, d)
        st, v = u.call("GET", "/api/etfs/official/low/view?amount=10000&days=90&otm=5"); self.assertEqual({r["symbol"] for r in v["rows"]}, {"KO", "PG"})
        self.assertEqual(a.call("POST", "/api/admin/official-etfs", {"low": {"name": "x", "positions": []}})[0], 400)
        db.kv_set("official_etfs", "")

    def test_v22_guide(self):
        u = self.reg("gd_u@x.com", "basico"); a = self.admin("gd_adm@x.com")
        st, g = u.call("GET", "/api/guide"); self.assertEqual(st, 200); self.assertEqual((g["bank_pays"], g["bank_charges"]), (1.43, 26.0)); self.assertTrue(g["quotes"])
        self.assertEqual(u.call("POST", "/api/admin/guide", {"bank_pays": 2})[0], 403)
        self.assertEqual(a.call("POST", "/api/admin/guide", {"bank_pays": 2.5})[0], 200); self.assertEqual(u.call("GET", "/api/guide")[1]["bank_pays"], 2.5)
        self.assertEqual(a.call("POST", "/api/admin/guide", {"bank_pays": -1})[0], 400); db.kv_set("guide", "")

    def test_v3_optcalc_math(self):
        from obb import optcalc as oc
        r = oc.analyze(100, oc.template_legs("covered_call", 100), iv=0.3)
        self.assertAlmostEqual(r["breakevens"][0], 100 - r["legs"][1]["premium"], delta=0.05)
        self.assertGreater(r["max_profit"], 0); self.assertLess(r["max_loss"], 0)
        ic = oc.analyze(100, oc.template_legs("iron_condor", 100), iv=0.3); self.assertEqual(len(ic["breakevens"]), 2); self.assertLess(ic["max_loss"], 0)
        lc = oc.analyze(100, oc.template_legs("long_call", 100), iv=0.3); self.assertIsNone(lc["max_profit"]); self.assertAlmostEqual(lc["max_loss"], -lc["net"], places=1)
        self.assertAlmostEqual(oc.price("C", 100, 100, 1, 0.2, 0.0) - oc.price("P", 100, 100, 1, 0.2, 0.0), 0, places=6)     # paridad put-call con r=0
        with self.assertRaises(oc.CalcError): oc.analyze(100, [])
        with self.assertRaises(oc.CalcError): oc.analyze(100, [{"type": "C", "side": 1, "strike": 100}] * 7)

    def test_v3_gex_math(self):
        from obb import optcalc as oc
        ch = [{"cp": "C", "strike": 100, "expiry": "2026-11-20", "oi": 1000, "gamma": 0.05}, {"cp": "P", "strike": 95, "expiry": "2026-11-20", "oi": 2000, "gamma": 0.04},
              {"cp": "C", "strike": 105, "expiry": "2026-11-20", "oi": 500, "gamma": 0.03}]
        g = oc.gex(100, ch); self.assertEqual((g["call_wall"], g["put_wall"]), (100, 95)); self.assertAlmostEqual(g["rows"][1]["call"], 0.05 * 1000 * 100 * 100 * 100 * 0.01, delta=1)
        self.assertLess([r for r in g["rows"] if r["strike"] == 95][0]["put"], 0)
        with self.assertRaises(oc.CalcError): oc.gex(100, ch, "2030-01-01")

    def test_v3_tools_api_and_gating(self):
        b = self.reg("t3_b@x.com", "basico"); i = self.reg("t3_i@x.com", "intermedio"); a = self.reg("t3_a@x.com", "avanzado")
        self.assertEqual(b.call("POST", "/api/opcalc", {"symbol": "KO", "template": "covered_call"})[0], 403)
        st, r = i.call("POST", "/api/opcalc", {"symbol": "KO", "template": "iron_condor", "iv": 0.3}); self.assertEqual(st, 200, r); self.assertEqual(len(r["breakevens"]), 2)
        self.assertEqual(i.call("POST", "/api/opcalc", {"symbol": "KO", "legs": [{"type": "C", "side": 1, "strike": 100, "qty": 1, "dte": 30}]})[0], 400)    # patas libres: solo Avanzado
        st, r = a.call("POST", "/api/opcalc", {"spot": 100, "iv": 0.3, "legs": [{"type": "C", "side": 1, "strike": 100, "qty": 1, "dte": 30}, {"type": "C", "side": -1, "strike": 110, "qty": 1, "dte": 30}]}); self.assertEqual(st, 200, r)
        self.assertEqual(a.call("POST", "/api/opcalc", {"spot": -1, "template": "long_call"})[0], 400)
        for path in ("/api/earnings?symbol=KO", "/api/gex?symbol=SPY"):
            self.assertEqual(b.call("GET", path)[0], 403); self.assertEqual(i.call("GET", path)[0], 403)
        st, e = a.call("GET", "/api/earnings?symbol=KO"); self.assertEqual(st, 200, e); self.assertTrue(e["rows"]); self.assertTrue(e["demo"])
        r0 = e["rows"][0]; self.assertAlmostEqual(r0["day_pct"], (r0["close"] / r0["prev_close"] - 1) * 100, delta=0.02)
        st, g = a.call("GET", "/api/gex?symbol=SPY"); self.assertEqual(st, 200, g); self.assertIn(g["call_wall"], [x["strike"] for x in g["rows"]])
        st, g2 = a.call("GET", "/api/gex?symbol=SPY&expiry=" + g["expiries"][0]); self.assertEqual(st, 200)
        self.assertEqual(a.call("GET", "/api/gex?symbol=bad!")[0], 400)
        st, d = b.call("GET", "/api/dividends/table?symbols=KO,PG"); self.assertEqual(st, 200); self.assertEqual(len(d["rows"]), 2)
        st, d = b.call("GET", "/api/dividends?symbol=KO"); self.assertEqual(st, 200); self.assertIsNone(d["history"])           # historial: Intermedio+
        st, d = i.call("GET", "/api/dividends?symbol=KO"); self.assertEqual(st, 200); self.assertIsNotNone(d["history"])

    def test_i18n_dictionaries(self):
        import re as _re
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "js")
        def load(l):
            s = open(os.path.join(base, f"i18n-{l}.js"), encoding="utf8").read(); return json.loads(s[s.index(f"OBB.DICT.{l} = ") + len(f"OBB.DICT.{l} = "):s.rindex("};") + 1])
        en, pt = load("en"), load("pt")
        self.assertEqual(set(en), set(pt))
        for k in en:
            self.assertEqual((k.count("{}"), k.count("{*}")), (en[k].count("{}"), en[k].count("{*}")), k); self.assertEqual((k.count("{}"), k.count("{*}")), (pt[k].count("{}"), pt[k].count("{*}")), k)
        for l in ("en", "pt"):
            self.assertTrue(os.path.exists(os.path.join(base, "..", f"manual.{l}.md")))


if __name__ == "__main__":
    unittest.main()
