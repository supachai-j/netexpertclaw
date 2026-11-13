"""Lazy proxy tests: instant initialize/tools/list, forwarding unchanged, fail-closed on stale cache, cache == live server."""
import json, os, pathlib, shutil, subprocess, sys, tempfile, time, unittest
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

ENVDUMP = r'''
import json, os, sys
tools = json.load(open(sys.argv[1]))["tools"]
for line in sys.stdin:
    m = json.loads(line); i = m.get("id"); meth = m.get("method")
    if meth == "initialize": print(json.dumps({"jsonrpc":"2.0","id":i,"result":{"protocolVersion":"2025-03-26","capabilities":{},"serverInfo":{"name":"f","version":"0"}}}), flush=True)
    elif meth == "tools/list": print(json.dumps({"jsonrpc":"2.0","id":i,"result":{"tools":tools}}), flush=True)
    elif meth == "tools/call": print(json.dumps({"jsonrpc":"2.0","id":i,"result":{"content":[{"type":"text","text":json.dumps(sorted(os.environ))}]}}), flush=True)
'''
HANG = r'''
import json, sys, time
tools = json.load(open(sys.argv[1]))["tools"]
for line in sys.stdin:
    m = json.loads(line); i = m.get("id"); meth = m.get("method")
    if meth == "initialize": print(json.dumps({"jsonrpc":"2.0","id":i,"result":{"protocolVersion":"2025-03-26","capabilities":{},"serverInfo":{"name":"f","version":"0"}}}), flush=True)
    elif meth == "tools/list": print(json.dumps({"jsonrpc":"2.0","id":i,"result":{"tools":tools}}), flush=True)
    elif meth == "tools/call": time.sleep(60)
'''

def run_child(src, lines, env_extra=None, timeout=30):
    with tempfile.TemporaryDirectory() as t:
        f = pathlib.Path(t) / "c.py"; f.write_text(src)
        env = dict(os.environ, **(env_extra or {}))
        p = subprocess.Popen([sys.executable, str(P), "--cache", str(CACHE), "--", sys.executable, str(f), str(CACHE)],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        out, errs = p.communicate("\n".join(json.dumps(x) if not isinstance(x, str) else x for x in lines) + "\n", timeout=timeout)
        return [json.loads(l) for l in out.splitlines()], errs

CALL = lambda i, name="parse_policy": {"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": name, "arguments": {}}}

class Hardening(unittest.TestCase):
    def test_px1_secrets_and_uv_tokens_not_passed(self):
        res, _ = run_child(ENVDUMP, [INIT, CALL(5)], env_extra={"UV_PUBLISH_TOKEN": "x", "UV_INDEX_PRIV_PASSWORD": "x", "UV_INSECURE_HOST": "x",
                                                                 "GITHUB_TOKEN": "x", "ANTHROPIC_API_KEY": "x", "UV_CACHE_DIR": "/tmp/uvc"})
        names = json.loads([r for r in res if r["id"] == 5][0]["result"]["content"][0]["text"])
        for bad in ("UV_PUBLISH_TOKEN", "UV_INDEX_PRIV_PASSWORD", "UV_INSECURE_HOST", "GITHUB_TOKEN", "ANTHROPIC_API_KEY"): self.assertNotIn(bad, names)
        self.assertIn("UV_CACHE_DIR", names); self.assertIn("PATH", names)
    def test_px2_malformed_input_does_not_crash(self):
        res, _ = run_child(FAKE, [INIT, "[1,2]", "42", "\"s\"", "null", '{"jsonrpc":"2.0","id":4,"method":5}', "{not json", {"jsonrpc": "2.0", "id": 6, "method": "ping"}])
        self.assertEqual([r.get("error", {}).get("code") for r in res[1:7]], [-32600, -32600, -32600, -32600, -32600, -32700])
        self.assertEqual(res[-1]["result"], {})
    def test_px3_hung_child_times_out_and_proxy_survives(self):
        res, errs = run_child(HANG, [INIT, CALL(8), {"jsonrpc": "2.0", "id": 9, "method": "ping"}], env_extra={"NETPAW_PROXY_CALL_TIMEOUT": "2"})
        self.assertEqual([r for r in res if r["id"] == 8][0]["error"]["code"], -32003)
        self.assertEqual([r for r in res if r["id"] == 9][0]["result"], {})
    def test_px4_only_cached_tools_and_tools_call_forwarded(self):
        res, _ = run_child(FAKE, [INIT, CALL(2, "apply_config"), {"jsonrpc": "2.0", "id": 3, "method": "resources/read", "params": {"uri": "file:///etc/passwd"}},
                                  {"jsonrpc": "2.0", "id": 4, "method": "prompts/list"}])
        self.assertEqual([r["error"]["code"] for r in res[1:4]], [-32602, -32601, -32601])
    def test_px5_unknown_protocol_version_falls_back(self):
        i = json.loads(json.dumps(INIT)); i["params"]["protocolVersion"] = "9999-01-01"
        res, _ = run_child(FAKE, [i]); self.assertEqual(res[0]["result"]["protocolVersion"], "2025-03-26")

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
    @unittest.skipUnless(shutil.which("uv") and os.environ.get("NETPAW_LIVE_TESTS") == "1", "set NETPAW_LIVE_TESTS=1 (needs uv + network)")
    def test_cache_matches_live_server(self):
        p = subprocess.run(["uv", "run", "--quiet", "--no-project", "--isolated", "--with", "mcp==1.30.0", "python", str(R / "scripts/gen_tools_cache.py"), "fwrule", "--check"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

if __name__ == "__main__":
    unittest.main()
