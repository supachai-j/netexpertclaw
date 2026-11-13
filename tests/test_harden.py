"""OWASP MCP cheat sheet #2/#5: strict input schemas advertised AND enforced. Needs uv + mcp, so gated by NETPAW_LIVE_TESTS=1."""
import json, os, pathlib, shutil, subprocess, sys, unittest
R = pathlib.Path(__file__).resolve().parent.parent
CODE = r'''
import asyncio, sys, json
sys.path.insert(0, sys.argv[1]); import server
async def go():
    tools = await server.mcp.list_tools()
    out = {"strict": all(t.inputSchema.get("additionalProperties") is False for t in tools), "n": len(tools)}
    name = sys.argv[2]; args = json.loads(sys.argv[3])
    try: await server.mcp.call_tool(name, args); out["extra_arg"] = "accepted"
    except Exception as e: out["extra_arg"] = "rejected" if "Extra inputs" in str(e) or "validation" in str(e).lower() else str(e)[:80]
    print(json.dumps(out))
asyncio.run(go())
'''
@unittest.skipUnless(shutil.which("uv") and os.environ.get("NETPAW_LIVE_TESTS") == "1", "set NETPAW_LIVE_TESTS=1 (needs uv)")
class Harden(unittest.TestCase):
    def check(self, srv, tool, args):
        p = subprocess.run(["uv", "run", "--quiet", "--no-project", "--isolated", "--with", "mcp==1.30.0", "python", "-c", CODE, str(R / "mcp" / srv), tool, json.dumps(args)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        r = json.loads(p.stdout.strip().splitlines()[-1]); self.assertTrue(r["strict"], r); self.assertEqual(r["extra_arg"], "rejected", r)
    def test_subnet_calc(self): self.check("subnet-calc", "subnet_calculator", {"cidr": "192.0.2.0/26", "evil": 1})
    def test_rfc_lookup(self): self.check("rfc-lookup", "get_rfc", {"number": "4271/../x", "evil": 1})   # rejected on the extra key before any network use
if __name__ == "__main__":
    unittest.main()
