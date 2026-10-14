import os, sys, tempfile, time, unittest, hmac, hashlib, json
os.environ["OBB_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from obb import auth, billing, db, flow, reports, strategies, providers, clock  # noqa: E402

TOS_CSV = """Strategy Report for MU
Symbol: MU
Id;Strategy;Side;Amount;Price;Date/Time;Trade P/L;P/L;Position
1;Vela Verde (OBB_VVV3);Buy to Open;+100;100.00;9/23/26 7:50 AM;;;
2;Vela Verde (OBB_VVV3);Sell to Close;-100;93.00;9/23/26 9:35 AM;($702.10);($702.10);
3;Vela Verde (OBB_VVV3);Buy to Open;+100;100.00;9/23/26 10:15 AM;;;
4;Vela Verde (OBB_VVV3);Sell to Close;-100;116.12;9/23/26 11:40 AM;"$1,612.40";$910.30;
5;Vela Roja de Apertura (OBB_VRV);Sell to Open;-100;50.00;9/24/26 7:50 AM;;;
6;Vela Roja de Apertura (OBB_VRV);Buy to Close;+100;29.44;9/24/26 8:25 AM;$2,056.00;$2,966.30;
"""

class Auth(unittest.TestCase):
    def test_trial_and_gate(self):
        u = auth.create_user("a@x.com", "password1", "A")
        self.assertEqual(auth.access_info(u)["reason"], "trial")
        db.x("UPDATE users SET trial_ends=? WHERE id=?", (int(time.time()) - 5, u["id"]))
        self.assertFalse(auth.access_info(auth.get_user(u["id"]))["access"])
        auth.admin_update(u["id"], "grant_days", 30)
        self.assertEqual(auth.access_info(auth.get_user(u["id"]))["reason"], "active")
        auth.admin_update(u["id"], "revoke")
        self.assertFalse(auth.access_info(auth.get_user(u["id"]))["access"])
    def test_validation_and_tokens(self):
        with self.assertRaises(ValueError): auth.create_user("bad", "password1")
        with self.assertRaises(ValueError): auth.create_user("b@x.com", "short")
        u = auth.create_user("c@x.com", "password1")
        with self.assertRaises(ValueError): auth.create_user("c@x.com", "password1")
        self.assertTrue(auth.verify_pw("password1", u["pw_hash"])); self.assertFalse(auth.verify_pw("nope", u["pw_hash"]))
        t = auth.make_token(u["id"]); self.assertEqual(auth.read_token(t), u["id"])
        self.assertIsNone(auth.read_token(t[:-2] + "xx")); self.assertIsNone(auth.read_token(auth.make_token(u["id"], ttl=-1)))

class Stripe(unittest.TestCase):
    def test_signature_and_events(self):
        body = b'{"x":1}'; t = str(int(time.time())); sec = "whsec_test"
        sig = hmac.new(sec.encode(), t.encode() + b"." + body, hashlib.sha256).hexdigest()
        self.assertTrue(billing.verify_signature(body, f"t={t},v1={sig}", sec))
        self.assertFalse(billing.verify_signature(body, f"t={t},v1={'0'*64}", sec))
        self.assertFalse(billing.verify_signature(body, f"t={int(t)-1000},v1={sig}", sec))
        u = auth.create_user("s@x.com", "password1")
        billing.handle_event({"type": "checkout.session.completed", "data": {"object": {"customer": "cus_1", "client_reference_id": str(u["id"])}}})
        self.assertEqual(auth.access_info(auth.get_user(u["id"]))["reason"], "active")
        billing.handle_event({"type": "customer.subscription.deleted", "data": {"object": {"customer": "cus_1"}}})
        db.x("UPDATE users SET trial_ends=0 WHERE id=?", (u["id"],))
        self.assertFalse(auth.access_info(auth.get_user(u["id"]))["access"])

class Reports(unittest.TestCase):
    def test_tos_parse_and_metrics(self):
        p = reports.parse("x.csv", TOS_CSV.encode())
        self.assertEqual(p["symbol"], "MU"); self.assertEqual(len(p["trades"]), 3)
        self.assertEqual(p["trades"][0]["pnl"], -702.10); self.assertEqual(p["trades"][1]["entry_ts"], "2026-09-23 10:15")
        s = reports.summarize(p["trades"])
        self.assertEqual(s["total"]["ops"], 3); self.assertEqual(s["total"]["wins"], 2); self.assertAlmostEqual(s["total"]["net"], 2966.30)
        self.assertTrue(any(x["absent"] and "Martillo" in x["name"] for x in s["strategies"]))
    def test_demo_matches_screenshot(self):
        reports.seed_demo(); rep = reports.load_report(1); T = rep["total"]
        self.assertEqual((T["ops"], T["wins"], T["losses"], T["net"]), (11, 5, 6, 4362.54)); self.assertEqual(round(T["hit_rate"], 1), 45.5)
        v = next(s for s in rep["strategies"] if "Verde" in s["name"])
        self.assertEqual((v["ops"], v["wins"], v["losses"], v["net"], v["avg_win"], v["avg_loss"], v["best"]), (10, 4, 6, 2306.54, 1582.17, -670.36, 1629.19))
        self.assertGreater(len(reports.to_xlsx(rep)), 5000)
    def test_bad_file(self):
        with self.assertRaises(reports.ReportError): reports.parse("x.csv", b"a,b\n1,2\n")

class NoOpenpyxl(unittest.TestCase):
    """La app debe leer .xlsx aunque openpyxl no esté instalado (caso real en Windows)."""
    def test_lite_reader(self):
        from obb import xlsxlite, service
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "Acciones_mas_importantes_por_Sector.xlsx")
        lite = xlsxlite._lite(path)
        self.assertTrue(any("Technology" in str(c) for _, rows in lite for r in rows for c in r))
        wl = service.parse_watchlist(path)
        self.assertEqual(len(wl), 11); self.assertEqual(wl["Technology"], ["NVDA", "AVGO", "AMD", "ANET", "PLTR"])
        reports.seed_demo() if not db.q1("SELECT 1 FROM reports") else None
        data = reports.to_xlsx(reports.load_report(1))
        rows = dict(xlsxlite._lite(data))["Datos"]
        self.assertEqual(rows[0][:3], ["#", "Estrategia", "Entrada"]); self.assertEqual(len(rows), 12)
        p = reports.parse("r.xlsx", data); self.assertEqual(len(p["trades"]), 11)

class Flow(unittest.TestCase):
    def test_oi_change(self):
        mk = lambda occ, vol, oi: {"occ": occ, "underlying": "AAA", "cp": "C", "strike": 10.0, "expiry": "2026-12-18", "volume": vol, "oi": oi, "last": 1.0}
        flow.save_close("2026-01-05", {"AAA": [mk("A1", 1000, 5000), mk("A2", 800, 2000), {**mk("A3", 500, 100), "expiry": "2026-01-05"}]})
        flow.save_morning("2026-01-06", {"AAA": [mk("A1", 0, 5900), mk("A2", 0, 1200)]})
        r = flow.compute("2026-01-05", "2026-01-06"); by = {c["occ"]: c for c in r["contracts"]}
        self.assertEqual(by["A1"]["d_oi"], 900); self.assertAlmostEqual(by["A1"]["pct"], 18.0); self.assertAlmostEqual(by["A1"]["conv"], 0.9)
        self.assertEqual(by["A1"]["label"], flow.LABEL_OPEN); self.assertEqual(by["A2"]["label"], flow.LABEL_CLOSE)
        self.assertEqual(by["A3"]["label"], flow.LABEL_EXP); self.assertEqual(r["summary"]["contracts"], 2)
        self.assertEqual(flow.available_pairs()[0], {"close_date": "2026-01-05", "morning_date": "2026-01-06"})

class Detectors(unittest.TestCase):
    def test_demo_injection_fires_every_strategy(self):
        d = providers.DemoProvider(); day = clock.effective_session()[0]; hit = set()
        for sym in list(providers.BASE_PRICES):
            sc = d._scenario(sym, day); ids = [s for s, i in strategies.scan_all(d.history(sym, "SCAN")).items() if i is not None]
            if sc <= 7: self.assertTrue(ids, f"{sym} escenario {sc} sin señal")
            hit.update(ids)
        self.assertEqual(hit, set(strategies.BY_ID))
    def test_vela_verde_exact(self):
        mk = lambda o, c: {"t": 1790000000, "o": o, "c": c, "h": max(o, c) + .1, "l": min(o, c) - .1, "v": 1}
        ok = [mk(10, 9), mk(9, 8), mk(8, 7.9), mk(7.9, 8.5), mk(8.5, 9.2)]
        self.assertTrue(strategies.vela_verde(ok, 4))
        self.assertFalse(strategies.vela_verde(ok[:3] + [mk(7.9, 8.5), mk(8.5, 8.2)], 4))

if __name__ == "__main__":
    unittest.main(verbosity=1)
