"""Findings from the tester cross-review (EV-1..EV-5, WK-1..WK-4, E-1/E-2) as regression tests."""
import json, pathlib, sys, time, unittest, io
R = pathlib.Path(__file__).resolve().parent.parent
for d in ("eve-lab", "wikipedia", "rfc-lookup", "_shared"): sys.path.insert(0, str(R / "mcp" / d))
import eve_core as eve, wiki_core as wiki, rfc_core as rfc, textclean
sys.path.insert(0, str(R / "tests")); from test_eve import unl

HIDDEN = ["\U000e0041", "\U000e0001", "\ufe0f", "\U000e0100", "\u2028", "\u2029", "\u034f", "\u061c", "\u180e", "\u3164", "\u200b", "\u202e", "\u2066", "\ufeff", "\u00ad", "\x1b", "\x07", "\u2063", "\ufffa"]


class Hidden(unittest.TestCase):
    def test_textclean_removes_all_but_keeps_text_tab_newline(self):
        raw = "A" + "".join(HIDDEN) + "B\tC\nD"
        self.assertEqual(textclean.strip_hidden(raw), "AB\tC\nD")
    def test_applied_in_every_core(self):
        raw = "x\U000e0041\U000e0042\U000e0043 CANARY\u2028y"
        self.assertEqual(wiki.clean(raw), "x CANARYy"); self.assertEqual(eve._s(raw), "x CANARYy"); self.assertEqual(rfc.strip_invisible(raw), "x CANARYy")
        self.assertEqual(rfc.clean(raw), ["x CANARYy"])
    def test_hidden_text_cannot_survive_in_eve_result(self):
        x = unl(["R1", "R2"], [("R1", "R2")]).replace('name="R1"', 'name="R1\U000e0049\U000e0047\U000e004e"', 1)
        self.assertEqual(json.dumps(eve.validate(x), ensure_ascii=True).count("\\udb40"), 0)


class EveFindings(unittest.TestCase):
    def test_ev1_parallel_links_are_not_a_single_link_spof(self):
        two = eve.validate(unl(["CORE1", "CORE2"], [("CORE1", "CORE2"), ("CORE1", "CORE2")]))
        self.assertFalse(any("SPOF links" in w for w in two["warnings"])); self.assertIn("No single-link SPOFs", two["passed"])
        one = eve.validate(unl(["CORE1", "CORE2"], [("CORE1", "CORE2")]))
        self.assertTrue(any("SPOF links" in w for w in one["warnings"]))
    def test_ev2_shared_segment_is_not_a_direct_forbidden_link(self):
        ifs = lambda n, i: f'<interface id="{i}" network_id="1"/>'
        nodes = "".join(f'<node id="{i}" name="{n}">{ifs(n, 0)}</node>' for i, n in enumerate(["CORE1", "HOST1", "DIST1", "CORE2"], 1))
        r = eve.validate(f'<lab name="m"><topology><nodes>{nodes}</nodes><networks><network id="1" name="mgmt" type="bridge"/></networks></topology></lab>')
        self.assertFalse(any("Forbidden adjacency" in f for f in r["failures"])); self.assertTrue(any("shares a multi-endpoint segment" in w for w in r["warnings"]))
        direct = eve.validate(unl(["HOST1", "CORE1"], [("HOST1", "CORE1")]))
        self.assertTrue(any("Forbidden adjacency (direct link)" in f for f in direct["failures"]))
    def test_ev3_message_explains_the_limit(self):
        nodes = "".join(f'<node id="{i}" name="N{i}"><interface id="0" network_id="1"/></node>' for i in range(eve.MAX_NET_MEMBERS + 1))
        with self.assertRaises(eve.UnlError) as c: eve.validate(f'<lab>{nodes}<network id="1"/></lab>')
        self.assertIn("split the segment", str(c.exception))
    def test_ev4_duplicate_ids_rejected(self):
        with self.assertRaises(eve.UnlError): eve.validate('<lab><node id="1" name="A"><interface id="0" network_id="1"/></node><node id="1" name="B"><interface id="0" network_id="1"/></node><network id="1"/></lab>')
        with self.assertRaises(eve.UnlError): eve.validate('<lab><node id="1" name="A"/><node id="1\u200b" name="B"/></lab>')
        with self.assertRaises(eve.UnlError): eve.validate('<lab><node id="1" name="A"/><network id="1"/><network id="1"/></lab>')
    def test_e1_partition_report_is_deterministic(self):
        x = unl(["R1", "R2", "R3", "R4", "R5", "R6"], [("R1", "R2"), ("R3", "R4"), ("R5", "R6")])
        first = [f for f in eve.validate(x)["failures"] if "partitioned" in f][0]
        self.assertEqual(first, [f for f in eve.validate(x)["failures"] if "partitioned" in f][0]); self.assertLess(first.index("R1"), first.index("R3"))


class Slow(unittest.TestCase):
    class Drip:
        headers = {"Content-Type": "application/json"}
        def read(self, n): time.sleep(0); return b"x"
    def test_wk1_overall_deadline_wiki_and_rfc(self):
        for core, err in ((wiki, wiki.WikiError), (rfc, rfc.RfcError)):
            old = core.TIMEOUT; core.TIMEOUT = 0.05
            try:
                with self.assertRaises(err) as c: core._read(self.Drip(), 10**9)
                self.assertIn("overall timeout", str(c.exception))
            finally: core.TIMEOUT = old


class WikiShapes(unittest.TestCase):
    def setUp(self): wiki._cache.clear(); self._f = wiki._fetch
    def tearDown(self): wiki._fetch = self._f
    def test_wk3_malformed_api_shapes_become_wikierror(self):
        for body in ('{"query": []}', '{"query": {"pages": "x"}}', '{"query": {"pages": [1]}}', '{"query": {"pages": [{"title": "t", "ns": 0, "extlinks": 5}]}}', '{"query": {"search": [5]}}', '{"query": {"search": 3}}', "[]", "null", "5"):
            wiki._cache.clear(); wiki._fetch = lambda u, b=body: b
            for fn, a in ((wiki.summary, ("T",)), (wiki.references, ("T",)), (wiki.categories, ("T",)), (wiki.content, ("T",)), (wiki.search, ("t",))):
                try: fn(*a)
                except wiki.WikiError: pass
                except Exception as e: self.fail(f"{fn.__name__} on {body!r} raised {type(e).__name__}: {e}")
    def test_wk4_other_namespaces_refused(self):
        wiki._fetch = lambda u: json.dumps({"query": {"pages": [{"title": "User:Someone", "ns": 2, "extract": "attacker text"}]}})
        with self.assertRaises(wiki.WikiError) as c: wiki.summary("User:Someone")
        self.assertIn("namespaces", str(c.exception))


if __name__ == "__main__":
    unittest.main()
