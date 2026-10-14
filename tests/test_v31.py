"""Pruebas de la versión 3.1: indicadores nuevos, referidos, casos del «¿Qué hubiera pasado si…?», earnings con tendencia y sectores."""
import os, sys, tempfile, threading, time, unittest
os.environ["OBB_DATA"] = tempfile.mkdtemp()
os.environ["OBB_DEMO"] = "1"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import server  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402
from obb import auth, db, referrals, rules, scenarios, service  # noqa: E402
from test_plans import Client  # noqa: E402


def C(o, h, l, c, v=100):
    return {"o": o, "h": h, "l": l, "c": c, "v": v}


class Indicators(unittest.TestCase):
    def ok(self, cond, candles, i=None):
        r = rules.validate({"side": "BULL", "conditions": [cond]})
        return rules.at(r, candles, len(candles) - 1 if i is None else i)

    def test_engulfing(self):
        up = [C(10, 10.5, 9.4, 9.6), C(9.5, 10.8, 9.3, 10.6)]
        self.assertTrue(self.ok({"type": "engulfing", "dir": "bull"}, up))
        self.assertFalse(self.ok({"type": "engulfing", "dir": "bear"}, up))
        small = [C(10, 10.5, 9.4, 9.6), C(9.7, 9.9, 9.6, 9.8)]
        self.assertFalse(self.ok({"type": "engulfing", "dir": "bull"}, small))
        dn = [C(9.6, 10.5, 9.5, 10), C(10.1, 10.2, 9.3, 9.4)]
        self.assertTrue(self.ok({"type": "engulfing", "dir": "bear"}, dn))

    def test_doji(self):
        self.assertTrue(self.ok({"type": "doji"}, [C(10, 11, 9, 10.05)]))
        self.assertFalse(self.ok({"type": "doji"}, [C(10, 11, 9, 10.8)]))
        self.assertTrue(self.ok({"type": "doji", "kind": "dragonfly"}, [C(10, 10.05, 8, 10.02)]))
        self.assertFalse(self.ok({"type": "doji", "kind": "gravestone"}, [C(10, 10.05, 8, 10.02)]))

    def test_breakout_and_golden(self):
        cc = [C(10, 10.2, 9.9, 10), C(10, 10.3, 9.9, 10.1), C(10, 11, 10, 10.9, 500)]
        self.assertTrue(self.ok({"type": "breakout", "n": 2, "dir": "up", "vol_mult": 2}, cc))
        cc[2] = C(10, 11, 10, 10.9, 90)
        self.assertFalse(self.ok({"type": "breakout", "n": 2, "dir": "up", "vol_mult": 2}, cc))
        self.assertTrue(self.ok({"type": "breakout", "n": 2, "dir": "up"}, cc))                    # sin exigir volumen
        series = [10] * 8 + [9.5, 9, 9, 9.5, 11, 13]
        cs = [C(p, p + .2, p - .2, p) for p in series]
        hits = [i for i in range(len(cs)) if self.ok({"type": "golden_cross", "fast": 2, "slow": 5, "dir": "golden"}, cs, i)]
        self.assertTrue(hits)
        with self.assertRaises(rules.RuleError): rules.validate({"side": "BULL", "conditions": [{"type": "golden_cross", "fast": 200, "slow": 50, "dir": "golden"}]})
        txt = rules.describe(rules.validate({"side": "BULL", "conditions": [{"type": "golden_cross", "dir": "death"}]}))
        self.assertIn("Cruz de la muerte", txt[0])


class Refs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.conn()

    def user(self, n, **kw):
        auth._fails.clear()
        return auth.create_user(f"ref{n}@x.com", "password1", f"R{n}", **kw)

    def test_flow_and_milestones(self):
        a = self.user("a")
        code = db.q1("SELECT ref_code FROM users WHERE id=?", (a["id"],))["ref_code"]
        self.assertTrue(code and len(code) == 7)
        self.assertFalse(referrals.register(a["id"], code))                  # no se puede referir a sí mismo
        kids = [self.user(f"k{i}", ref=code)["id"] for i in range(20)]
        o = referrals.overview(a["id"]); self.assertEqual((o["registered"], o["qualified"]), (20, 0))
        db.x("UPDATE users SET sub_status='active', sub_ends=? WHERE id=?", (int(time.time()) + 86400 * 30, a["id"]))
        r = referrals.qualify(kids[0]); self.assertEqual(r["qualified"], 1)
        self.assertIsNone(referrals.qualify(kids[0]))                         # idempotente
        o = referrals.overview(a["id"]); self.assertEqual(o["discounts_waiting"], 1)
        self.assertEqual([w["status"] for w in o["rewards"] if w["kind"] == "disc"], ["active"])
        for k in kids[1:9]: referrals.qualify(k)
        self.assertFalse([w for w in referrals.overview(a["id"])["rewards"] if w["kind"] == "free"])
        r = referrals.qualify(kids[9]); self.assertEqual(r["milestones"][0]["months"], 6)
        u = auth.get_user(a["id"]); self.assertGreater(u["reward_until"], time.time() + 170 * 86400)
        for k in kids[10:]: referrals.qualify(k)
        u = auth.get_user(a["id"]); self.assertGreater(u["reward_until"], time.time() + 530 * 86400)   # 6 + 12 meses
        self.assertEqual(len([w for w in referrals.overview(a["id"])["rewards"] if w["kind"] == "free"]), 2)
        referrals.on_invoice_paid(a["id"])
        st = [w["status"] for w in referrals.overview(a["id"])["rewards"] if w["kind"] == "disc"]
        self.assertEqual(st.count("active"), 1); self.assertEqual(st.count("used"), 1)

    def test_reward_gives_access_and_plan(self):
        u = self.user("free", plan="basico")
        db.x("UPDATE users SET trial_ends=?, reward_until=? WHERE id=?", (int(time.time()) - 10, int(time.time()) + 3 * 86400, u["id"]))
        pu = auth.public_user(auth.get_user(u["id"]))
        self.assertEqual((pu["access"], pu["reason"], pu["plan"]), (True, "reward", "avanzado"))
        db.x("UPDATE users SET reward_until=? WHERE id=?", (int(time.time()) - 10, u["id"]))
        self.assertFalse(auth.access_info(auth.get_user(u["id"]))["access"])

    def test_claim_rules_and_masking(self):
        a, b = self.user("c1"), self.user("c2")
        code = referrals.ensure_code(a["id"])
        with self.assertRaises(ValueError): referrals.claim(b["id"], "ZZZZZZZ")
        with self.assertRaises(ValueError): referrals.claim(a["id"], code)
        referrals.claim(b["id"], code)
        with self.assertRaises(ValueError): referrals.claim(b["id"], code)    # ya tiene referidor
        row = referrals.overview(a["id"])["referred"][0]
        self.assertNotIn("ref", row["who"].split("@")[1]); self.assertIn("***", row["who"])
        with self.assertRaises(ValueError): referrals.set_rules({"disc_pct": 120, "milestones": [{"n": 5, "months": 1}]})
        self.assertEqual(referrals.set_rules({"disc_pct": 25, "milestones": [{"n": 5, "months": 2}]})["disc_pct"], 25)
        referrals.set_rules(referrals.DEFAULT_RULES)


class Http(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.bootstrap()
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler); cls.srv.daemon_threads = True
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.port = cls.srv.server_address[1]
        service.SERVICE.refresh_quotes()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def reg(self, email, plan="basico", ref=None, admin=False):
        auth._fails.clear()
        c = Client(self.port)
        st, d = c.call("POST", "/api/auth/register", {"email": email, "password": "password1", "plan": plan, "ref": ref})
        self.assertEqual(st, 201, d)
        if admin:
            db.x("UPDATE users SET role='admin' WHERE email=?", (email,))
        return c

    def test_sectors_builtin_and_editable(self):
        self.assertEqual(len(service.SERVICE.sectors()), 11)
        self.assertTrue(all(len(v) == 5 for v in service.SERVICE.sectors().values()))
        self.assertEqual(db.kv_get("sectors_seeded"), "1")
        a = self.reg("sec_a@x.com", admin=True); u = self.reg("sec_u@x.com", "avanzado")
        self.assertEqual(u.call("POST", "/api/admin/sector", {"sector": "Technology", "symbol": "MSFT"})[0], 403)
        self.assertEqual(a.call("POST", "/api/admin/sector", {"sector": "Technology", "symbol": "msft"})[0], 200)
        self.assertIn("MSFT", service.SERVICE.sectors()["Technology"])
        self.assertEqual(a.call("DELETE", "/api/admin/sector", {"sector": "Technology", "symbol": "MSFT"})[0], 200)
        self.assertNotIn("MSFT", service.SERVICE.sectors()["Technology"])
        self.assertEqual(a.call("POST", "/api/admin/sector", {"sector": "Cripto", "symbol": "COIN"})[0], 200)
        self.assertEqual(a.call("DELETE", "/api/admin/sector", {"sector": "Cripto"})[0], 200)
        self.assertNotIn("Cripto", service.SERVICE.sectors())
        self.assertEqual(a.call("POST", "/api/admin/sector", {"sector": "X", "symbol": "bad symbol!"})[0], 400)

    def test_referral_api(self):
        a = self.reg("api_ref_a@x.com", "intermedio")
        st, o = a.call("GET", "/api/referrals"); self.assertEqual(st, 200); code = o["code"]
        self.assertIn("?ref=" + code, o["link"])
        b = self.reg("api_ref_b@x.com", "basico", ref=code.lower())          # el código no distingue mayúsculas
        st, o = a.call("GET", "/api/referrals"); self.assertEqual((o["registered"], o["qualified"]), (1, 0))
        self.assertEqual(b.call("GET", "/api/admin/referrals")[0], 403)
        adm = self.reg("api_ref_adm@x.com", admin=True)
        st, ov = adm.call("GET", "/api/admin/referrals"); self.assertEqual(st, 200)
        pend = [p for p in ov["pending"] if p["referrer"] == "api_ref_a@x.com"]; self.assertEqual(len(pend), 1)
        st, r = adm.call("POST", "/api/admin/referrals/qualify", {"user_id": pend[0]["referred_id"]}); self.assertEqual(st, 200, r)
        self.assertEqual(adm.call("POST", "/api/admin/referrals/qualify", {"user_id": pend[0]["referred_id"]})[0], 400)
        st, o = a.call("GET", "/api/referrals"); self.assertEqual(o["qualified"], 1)
        self.assertEqual(adm.call("POST", "/api/admin/referrals/rules", {"disc_pct": 20, "milestones": [{"n": 10, "months": 6}, {"n": 20, "months": 12}]})[0], 200)
        self.assertEqual(adm.call("POST", "/api/admin/referrals/rules", {"disc_pct": -1, "milestones": []})[0], 400)
        # registro con código inválido: no bloquea
        self.reg("api_ref_c@x.com", ref="NOEXISTE")

    def test_whatif_cases(self):
        a = self.reg("wi_a@x.com", admin=True); u = self.reg("wi_u@x.com", "basico")
        st, d = u.call("GET", "/api/whatif/examples"); self.assertEqual(st, 200); self.assertGreaterEqual(len(d["examples"]), 9); self.assertEqual(d["mine"], [])
        for ex in d["examples"]:
            st, r = u.call("POST", "/api/whatif", {"shares": ex["shares"], "otm": ex["otm"], "iv": ex["iv"], "prices": ex["prices"]}); self.assertEqual(st, 200, ex["id"])
        body = {"title": "Mi caso", "symbol": "xyz", "shares": 100, "otm": 5, "iv": 30, "prices": "10, 9, 8, 9"}
        st, r = u.call("POST", "/api/whatif/cases", body); self.assertEqual(st, 201, r); cid = r["case"]["id"]
        st, d = u.call("GET", "/api/whatif/examples"); self.assertEqual([c["id"] for c in d["mine"]], [cid]); self.assertEqual(d["mine"][0]["symbol"], "XYZ")
        st, d2 = a.call("GET", "/api/whatif/examples"); self.assertEqual(d2["mine"], [])          # los casos propios no se ven entre usuarios
        self.assertEqual(u.call("POST", "/api/whatif/cases", {**body, "prices": "10"})[0], 400)
        self.assertEqual(u.call("POST", "/api/whatif/cases", {**body, "shares": 0})[0], 400)
        self.assertEqual(u.call("POST", "/api/admin/whatif/cases", body)[0], 403)
        st, r = a.call("POST", "/api/admin/whatif/cases", {**body, "title": "Caso oficial"}); self.assertEqual(st, 201)
        st, d = u.call("GET", "/api/whatif/examples"); self.assertIn("Caso oficial", [c["title"] for c in d["examples"]])
        self.assertEqual(u.call("DELETE", "/api/whatif/cases/" + cid)[0], 200)
        self.assertEqual(u.call("GET", "/api/whatif/examples")[1]["mine"], [])
        self.assertEqual(a.call("DELETE", "/api/admin/whatif/cases/" + r["case"]["id"])[0], 200)

    def test_earnings_twelve_with_trend(self):
        a = self.reg("ea_a@x.com", "avanzado")
        st, e = a.call("GET", "/api/earnings?symbol=KO"); self.assertEqual(st, 200, e)
        self.assertEqual(len(e["rows"]), 12)
        t = e["trend"]; self.assertIn(t["vol"], ("up", "down", "flat")); self.assertEqual(len(t["ma3"]), 12)
        self.assertEqual(sum(e["hist"]["counts"]), 12); self.assertEqual(len(e["hist"]["labels"]), 8)
        self.assertTrue(all("surprise_pct" in r for r in e["rows"]))

    def test_rules_api_new_types(self):
        a = self.reg("ru_a@x.com", "avanzado")
        for cond in ({"type": "doji", "max_body_pct": 8, "kind": "any"}, {"type": "engulfing", "dir": "bull", "trend_bars": 3},
                     {"type": "golden_cross", "fast": 50, "slow": 200, "dir": "golden"}, {"type": "breakout", "n": 20, "dir": "down", "vol_mult": 1.5}):
            st, r = a.call("POST", "/api/custom", {"name": cond["type"], "rule": {"side": "BULL", "conditions": [cond]}}); self.assertEqual(st, 201, r)
            st, d = a.call("GET", "/api/signals"); self.assertEqual(st, 200)
            self.assertEqual(len(d["custom"]), 1)
            a.call("DELETE", f"/api/custom/{r['id']}")


if __name__ == "__main__":
    unittest.main()
