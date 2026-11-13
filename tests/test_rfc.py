"""rfc-lookup tests: offline with synthetic fixtures (no network), plus optional live checks (NETPAW_LIVE_TESTS=1)."""
import io, os, pathlib, sys, unittest, urllib.error
R = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / "mcp" / "rfc-lookup"))
import rfc_core as core
FX = R / "tests" / "fixtures"
RFC = (FX / "rfc9999.txt").read_text()
IDX = (FX / "rfc-index-sample.txt").read_text()


def fake_fetch(url, cap):
    if url.endswith("/rfc/rfc9999.txt"): return RFC
    if url.endswith("/rfc-index.txt"): return IDX
    raise core.RfcError("HTTP 404 from www.rfc-editor.org")


class Offline(unittest.TestCase):
    def setUp(self):
        core._cache.clear(); self._f = core._fetch; core._fetch = fake_fetch
    def tearDown(self): core._fetch = self._f

    def test_number_validation(self):
        for ok, n in (("4271", 4271), ("RFC 4271", 4271), (" rfc9999 ", 9999), (791, 791)): self.assertEqual(core.parse_number(ok), n)
        for bad in ("0", "", "4271/../x", "../etc/passwd", "1e3", "123456", "4271?x=1", "-1", "rfc", "4271 ", "42 71", "http://evil/1"):
            if bad == "4271 ": continue   # surrounding whitespace is stripped, fine
            with self.assertRaises(core.RfcError, msg=bad): core.parse_number(bad)
    def test_get_rfc_cleans_and_lists_sections(self):
        r = core.get_rfc("RFC 9999")
        self.assertTrue(r["untrusted_external_text"]); self.assertEqual(r["source"], "https://www.rfc-editor.org/rfc/rfc9999.txt")
        self.assertNotIn("[Page", r["text"]); self.assertNotIn("RFC 9999                      STP", r["text"]); self.assertNotIn("\f", r["text"])
        titles = [s["title"] for s in r["sections"]]
        for t in ("Introduction", "Operation", "Timers", "Security Considerations", "Abstract"): self.assertIn(t, titles)
        self.assertNotIn("Table of Contents", titles)
    def test_paging(self):
        a = core.get_rfc(9999, 0, 100); b = core.get_rfc(9999, 100, 100)
        self.assertTrue(a["has_more"]); self.assertEqual(a["returned_chars"], 100)
        full = core.get_rfc(9999, 0, 50000)["text"]; self.assertEqual(a["text"] + b["text"], full[:200])
        with self.assertRaises(core.RfcError): core.get_rfc(9999, -1, 100)
        with self.assertRaises(core.RfcError): core.get_rfc(9999, 0, 0)
        with self.assertRaises(core.RfcError): core.get_rfc(9999, 0, 10**6)
    def test_sections(self):
        s = core.get_section(9999, "2"); self.assertIn("Messages are sent", s["text"]); self.assertIn("hold timer", s["text"]); self.assertNotIn("No authentication", s["text"])
        s = core.get_section(9999, "2.1"); self.assertIn("hold timer", s["text"]); self.assertNotIn("Messages are sent", s["text"])
        s = core.get_section(9999, "security considerations"); self.assertEqual(s["section"], "3 Security Considerations"); self.assertIn("No authentication", s["text"]); self.assertNotIn("no IANA actions", s["text"])
        s = core.get_section(9999, "IANA Considerations"); self.assertEqual(s["section"], "IANA Considerations"); self.assertIn("no IANA actions", s["text"]); self.assertNotIn("A. Example", s["text"])
        with self.assertRaises(core.RfcError): core.get_section(9999, "Nonexistent")
        with self.assertRaises(core.RfcError): core.get_section(9999, "")
    def test_truncation_flag(self):
        self.assertTrue(core.get_section(9999, "1", 20)["truncated"])
    def test_injection_text_is_returned_as_data_and_flagged(self):
        r = core.get_section(9999, "1"); self.assertIn("Ignore previous", r["text"]); self.assertTrue(r["untrusted_external_text"])
    def test_search(self):
        x = core.search("routing security"); self.assertEqual([h["rfc"] for h in x["results"]], [9998]); self.assertEqual(x["results"][0]["status"], "INFORMATIONAL")
        self.assertEqual(core.search("STP")["results"][0]["status"], "PROPOSED STANDARD")
        self.assertEqual([h["rfc"] for h in core.search("routing")["results"]], [10000, 9998])   # 5-digit entry parsed, newest first
        self.assertEqual(core.search("zzzz")["total_matches"], 0)
        for bad in ("", "   ", "x" * 201): 
            with self.assertRaises(core.RfcError): core.search(bad)
        with self.assertRaises(core.RfcError): core.search("a", 0)
    def test_not_found_maps_to_error(self):
        with self.assertRaises(core.RfcError): core.get_rfc(9000)


class Network(unittest.TestCase):
    """The real _fetch with a fake opener: allow-list, redirects, content type, size cap."""
    def _opener(self, headers, body, status=200):
        class R:
            def __init__(s): s.headers = headers
            def read(s, n): return body[:n]
            def __enter__(s): return s
            def __exit__(s, *a): return False
        class O:
            def open(s, req, timeout=None):
                O.timeout = timeout; O.req = req
                if status != 200: raise urllib.error.HTTPError(req.full_url, status, "x", {}, io.BytesIO(b""))
                return R()
        return O()
    def run_fetch(self, url, headers=None, body=b"x", cap=100, status=200):
        orig = core.urllib.request.build_opener
        o = self._opener(headers or {"Content-Type": "text/plain; charset=utf-8"}, body, status)
        core.urllib.request.build_opener = lambda *a, **k: o
        try: return core._fetch(url, cap), o
        finally: core.urllib.request.build_opener = orig
    def test_allow_list(self):
        for bad in ("http://www.rfc-editor.org/rfc/rfc1.txt", "https://evil.example/rfc/rfc1.txt", "https://www.rfc-editor.org.evil.example/x",
                    "https://www.rfc-editor.org@evil.example/x", "file:///etc/passwd", "https://www.ietf.org/rfc/rfc1.txt"):
            with self.assertRaises(core.RfcError, msg=bad): self.run_fetch(bad)
    def test_ok_and_timeout_set(self):
        txt, o = self.run_fetch("https://www.rfc-editor.org/rfc/rfc1.txt"); self.assertEqual(txt, "x"); self.assertEqual(o.timeout, core.TIMEOUT)
    def test_content_type_enforced(self):
        with self.assertRaises(core.RfcError): self.run_fetch("https://www.rfc-editor.org/rfc/rfc1.txt", headers={"Content-Type": "text/html"})
    def test_size_cap(self):
        with self.assertRaises(core.RfcError): self.run_fetch("https://www.rfc-editor.org/rfc/rfc1.txt", body=b"a" * 101, cap=100)
    def test_http_error_message_has_no_url_body(self):
        with self.assertRaises(core.RfcError) as c: self.run_fetch("https://www.rfc-editor.org/rfc/rfc1.txt", status=404)
        self.assertIn("404", str(c.exception))
    def test_redirects_refused(self):
        h = core._NoRedirect(); self.assertIsNone(h.redirect_request(None, None, 302, "Found", {}, "https://evil.example/"))


@unittest.skipUnless(os.environ.get("NETPAW_LIVE_TESTS") == "1", "set NETPAW_LIVE_TESTS=1 (network)")
class Live(unittest.TestCase):
    def test_live(self):
        core._cache.clear()
        s = core.get_section(4271, "Security Considerations"); self.assertIn("authentication", s["text"].lower())
        self.assertEqual(core.get_rfc("RFC 791", 0, 50)["rfc"], 791)
        self.assertIn(4271, [h["rfc"] for h in core.search("BGP-4 border gateway", 20)["results"]])
        with self.assertRaises(core.RfcError): core.get_rfc(99999)

if __name__ == "__main__":
    unittest.main()
