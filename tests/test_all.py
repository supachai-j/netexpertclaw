import json, subprocess, sys, pathlib, unittest
R = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / "mcp" / "subnet-calc")); sys.path.insert(0, str(R / "scripts"))
import core

class Core(unittest.TestCase):
    def test_v4(self):
        r = core.subnet_v4("192.0.2.0/24")
        self.assertEqual((r["netmask"], r["wildcard"], r["usable_hosts"], r["first_host"], r["last_host"], r["next"], r["previous"]),
                         ("255.255.255.0", "0.0.0.255", "254", "192.0.2.1", "192.0.2.254", "192.0.3.0/24", "192.0.1.0/24"))
    def test_doc_range(self):
        self.assertIn("documentation", core.subnet_v4("192.0.2.0/24")["classification"])
        self.assertEqual(core.subnet_v4("10.0.0.0/8")["classification"], "private")
    def test_p2p(self):
        self.assertEqual(core.subnet_v4("10.1.1.0/31")["usable_hosts"], "2")
        self.assertEqual(core.subnet_v4("10.1.1.0/30")["usable_hosts"], "2")
    def test_edges(self):
        self.assertIsNone(core.subnet_v4("0.0.0.0/0")["previous"]); self.assertIsNone(core.subnet_v4("255.255.255.255/32")["next"])
    def test_host_bits_rejected(self):
        with self.assertRaises(ValueError): core.subnet_v4("10.1.1.5/24")
        with self.assertRaises(ValueError): core.subnet_v6("fe80::1%eth0/64")
        with self.assertRaises(ValueError): core.subnet_v6("10.0.0.0/8")
    def test_v6(self):
        r = core.subnet_v6("2001:db8::/48")
        self.assertEqual((r["count_of_64s"], r["note"]), ("65536", "site allocation"))
        self.assertEqual(core.subnet_v6("::/0")["count_of_64s"], str(2**64))
    def test_same(self):
        self.assertTrue(core.same_subnet("10.0.0.1", "10.0.0.200", 24)["same_subnet"])
        self.assertFalse(core.same_subnet("10.0.0.1", "10.0.1.1", 24)["same_subnet"])

class Build(unittest.TestCase):
    def test_lint_and_build(self):
        self.assertEqual(subprocess.run([sys.executable, str(R/"scripts/lint.py")]).returncode, 0)
        self.assertEqual(subprocess.run([sys.executable, str(R/"scripts/build.py"), "--root", "/x"]).returncode, 0)
        oc = (R/"dist/openclaw/skills/subnet-calculator/SKILL.md").read_text()
        self.assertIn('"openclaw"', oc); self.assertIn('"uv"', oc)
        self.assertIn("allow_implicit_invocation: true", (R/"dist/codex/skills/subnet-calculator/agents/openai.yaml").read_text())
        self.assertIn("[mcp_servers.subnet-calc]", (R/"dist/codex/config.toml.snippet").read_text())
        self.assertIn("/x/mcp/subnet-calc/server.py", (R/"dist/thclaws/.thclaws/mcp.json").read_text())
        self.assertIn("CLAUDE_PLUGIN_ROOT", (R/".mcp.json").read_text())
        self.assertTrue((R/"dist/hermes/skills/netpaw/subnet-calculator/SKILL.md").exists())

if __name__ == "__main__":
    unittest.main()
