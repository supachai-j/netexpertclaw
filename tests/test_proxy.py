"""Lazy proxy tests: instant initialize/tools/list, forwarding unchanged, fail-closed on stale cache, cache == live server."""
import json, pathlib, shutil, subprocess, sys, tempfile, time, unittest
R = pathlib.Path(__file__).resolve().parent.parent
P = R / "mcp/fwrule/proxy.py"
CACHE = R / "mcp/fwrule/tools.cache.json"
sys.path.insert(0, str(R / "mcp/fwrule")); import proxy

FAKE = r'''
import json, sys
tools = json.load(open(sys.argv[1]))["tools"]
for line in sys.stdin:
    m = json.loads(line); i = m.get("id"); meth = m.get("method")
    if meth == "initialize": print(json.dumps({"jsonrpc":"2.0","id":i,"result":{"protocolVersion":"2025-03-26","capabilities":{},"serverInfo":{"name":"fake","version":"0"}}}), flush=True)
    elif meth == "tools/list": print(json.dumps({"jsonrpc":"2.0","id":i,"result":{"tools":tools}}), flush=True)
    elif meth == "tools/call": print(json.dumps({"jsonrpc":"2.0","id":i,"result":{"content":[{"type":"text","text":"echo:"+json.dumps(m["params"], sort_keys=True)}],"isError":False}}), flush=True)
'''

def session(cache, child_cache, lines, timeout=20):
    with tempfile.TemporaryDirectory() as t:
        f = pathlib.Path(t) / "fake.py"; f.write_text(FAKE)
        p = subprocess.Popen([sys.executable, str(P), "--cache", str(cache), "--", sys.executable, str(f), str(child_cache)],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, errs = p.communicate("\n".join(json.dumps(x) for x in lines) + "\n", timeout=timeout)
        return [json.loads(l) for l in out.splitlines()], errs

INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}

class Proxy(unittest.TestCase):
    def test_cache_integrity(self):
        c = json.loads(CACHE.read_text()); self.assertEqual(proxy.tools_hash(c["tools"]), c["sha256"])
        self.assertTrue(all(t["annotations"]["readOnlyHint"] for t in c["tools"]))
    def test_initialize_and_list_are_instant_and_child_not_started(self):
        t0 = time.time()
        res, _ = session(CACHE, "/nonexistent", [INIT, {"jsonrpc": "2.0", "method": "notifications/initialized"}, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, {"jsonrpc": "2.0", "id": 3, "method": "ping"}])
        self.assertLess(time.time() - t0, 3)
        self.assertEqual(res[0]["result"]["serverInfo"], json.loads(CACHE.read_text())["serverInfo"])
        self.assertEqual({t["name"] for t in res[1]["result"]["tools"]}, {"analyze_firewall_rule_overlap", "batch_analyze_overlap", "list_supported_vendors", "parse_policy"})
        self.assertEqual(res[2]["result"], {})   # fake child path is bogus: it was never started
    def test_call_forwarded_unchanged(self):
        params = {"name": "parse_policy", "arguments": {"vendor": "ios", "ruleset_payload": "x\u00e9 \u0e44"}}
        res, _ = session(CACHE, CACHE, [INIT, {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": params}])
        r = [x for x in res if x["id"] == 7][0]["result"]
        self.assertEqual(r["content"][0]["text"], "echo:" + json.dumps(params, sort_keys=True))
    def test_stale_cache_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            c = json.loads(CACHE.read_text()); c["tools"].append({"name": "apply_config", "inputSchema": {"type": "object"}})
            child = pathlib.Path(t) / "child.json"; child.write_text(json.dumps(c))   # live server "gained" a tool
            res, errs = session(CACHE, child, [INIT, {"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": "parse_policy", "arguments": {}}}])
            r = [x for x in res if x["id"] == 9][0]
            self.assertIn("error", r); self.assertIn("regenerate", r["error"]["message"]); self.assertIn("differs", errs)
    def test_corrupt_cache_refuses_to_start(self):
        with tempfile.TemporaryDirectory() as t:
            c = json.loads(CACHE.read_text()); c["tools"][0]["description"] = "tampered"; bad = pathlib.Path(t) / "bad.json"; bad.write_text(json.dumps(c))
            p = subprocess.run([sys.executable, str(P), "--cache", str(bad), "--", "true"], capture_output=True, text=True, input="")
            self.assertNotEqual(p.returncode, 0); self.assertIn("corrupted", p.stderr)
    @unittest.skipUnless(shutil.which("uv"), "uv needed")
    def test_cache_matches_live_server(self):
        p = subprocess.run(["uv", "run", "--quiet", "--no-project", "--isolated", "--with", "mcp==1.30.0", "python", str(R / "scripts/gen_tools_cache.py"), "fwrule", "--check"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

if __name__ == "__main__":
    unittest.main()
