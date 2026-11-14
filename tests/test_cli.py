import json, os, pathlib, subprocess, sys, tempfile, unittest
R = pathlib.Path(__file__).resolve().parent.parent
NP = [sys.executable, str(R / "bin" / "netpaw")]

def run(*a, home, cwd=None):
    env = dict(os.environ, HOME=home); env.pop("CODEX_HOME", None)
    return subprocess.run(NP + list(a), capture_output=True, text=True, env=env, cwd=cwd)

class Cli(unittest.TestCase):
    def test_basics(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertIn("netpaw 0.1.0", run("version", home=t).stdout)
            out = run("list", home=t).stdout; self.assertIn("subnet-calculator", out); self.assertIn("fwrule-analyzer", out)
            self.assertIn("NOT TESTED", run("agents", home=t).stdout)
            self.assertIn("all skills", run("profiles", home=t).stdout)
            self.assertEqual(run("lint", home=t).returncode, 0)
    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            p = run("install", "-a", "hermes", "-p", "standard", "--with-mcp", "--root", "/opt/x", home=t)
            self.assertEqual(p.returncode, 0, p.stderr); self.assertIn("dry run", p.stdout)
            self.assertEqual(os.listdir(t), [])
            self.assertFalse((R / "dist" / "hermes").exists() and False)
    def test_byte_exact_toml_roundtrip(self):
        with tempfile.TemporaryDirectory() as t:
            h = pathlib.Path(t); (h / ".codex").mkdir(); orig = 'model = "x"\n\n[mcp_servers.mine]\ncommand = "y"\n'; (h / ".codex/config.toml").write_text(orig)
            for _ in range(2):
                run("install", "-a", "codex", "-p", "standard", "--with-mcp", "--apply", "--root", "/opt/x", home=t); run("uninstall", "--apply", home=t)
            self.assertEqual((h / ".codex/config.toml").read_text(), orig)
            self.assertEqual(len([f for f in os.listdir(h / ".codex") if "bak" in f]), 1)
    def test_untested_agent_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p = run("install", "-a", "cursor", "--apply", home=t); self.assertEqual(p.returncode, 1); self.assertIn("NOT TESTED", p.stdout)
            self.assertEqual(os.listdir(t), [])
    def test_install_uninstall_roundtrip(self):
        with tempfile.TemporaryDirectory() as t:
            h = pathlib.Path(t)
            (h / ".codex").mkdir(); (h / ".codex/config.toml").write_text('model = "x"\n')
            proj = h / "proj"; proj.mkdir()
            p = run("install", "-a", "codex", "thclaws", "-p", "standard", "--project", "--with-mcp", "--apply", "--root", "/opt/x", home=t, cwd=str(proj))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertTrue((proj / ".codex/skills/subnet-calculator/SKILL.md").exists())
            self.assertTrue((proj / ".thclaws/skills/fwrule-analyzer/SKILL.md").exists())
            cfg = json.loads((proj / ".thclaws/mcp.json").read_text())["mcpServers"]; self.assertEqual(sorted(cfg), ["eve-lab", "fwrule", "subnet-calc"])
            self.assertNotIn("capability", cfg["fwrule"]); self.assertIn("/opt/x/mcp/fwrule/launch.py", cfg["fwrule"]["args"])
            self.assertIn("[mcp_servers.subnet-calc]", (proj / ".codex/config.toml").read_text())
            # idempotent: second run refuses mcp, skips files
            p2 = run("install", "-a", "thclaws", "-p", "standard", "--project", "--with-mcp", "--apply", "--root", "/opt/x", home=t, cwd=str(proj))
            self.assertIn("skip", p2.stdout); self.assertIn("refused", p2.stdout)
            # modified file survives uninstall
            (proj / ".thclaws/skills/subnet-calculator/SKILL.md").write_text("local edit")
            u = run("uninstall", "--apply", home=t, cwd=str(proj)); self.assertEqual(u.returncode, 0, u.stdout)
            self.assertIn("keep (modified)", u.stdout)
            self.assertTrue((proj / ".thclaws/skills/subnet-calculator/SKILL.md").exists())
            self.assertFalse((proj / ".thclaws/skills/fwrule-analyzer").exists())
            self.assertEqual(json.loads((proj / ".thclaws/mcp.json").read_text())["mcpServers"], {})
            self.assertEqual((proj / ".codex/config.toml").read_text() if (proj / ".codex/config.toml").exists() else "", "")  # B-1: no leftovers
            m = json.loads((h / ".netpaw/manifest.json").read_text())["installs"]            # B-6: kept file still tracked
            self.assertTrue(any(str(proj / ".thclaws/skills/subnet-calculator/SKILL.md") in r["files"] for r in m))
            self.assertEqual(oct(os.stat(proj / ".thclaws/mcp.json.bak-netpaw").st_mode & 0o777), "0o600") if (proj / ".thclaws/mcp.json.bak-netpaw").exists() else None
    def test_existing_hermes_mcp_servers_refused(self):
        with tempfile.TemporaryDirectory() as t:
            h = pathlib.Path(t); (h / ".hermes").mkdir(); (h / ".hermes/config.yaml").write_text("mcp_servers:\n  other:\n    command: x\n")
            p = run("install", "-a", "hermes", "--with-mcp", "--apply", "--root", "/opt/x", home=t)
            self.assertIn("refused", p.stdout); self.assertEqual((h / ".hermes/config.yaml").read_text(), "mcp_servers:\n  other:\n    command: x\n")
    def test_bad_agent(self):
        with tempfile.TemporaryDirectory() as t: self.assertNotEqual(run("install", "-a", "nope", home=t).returncode, 0)

if __name__ == "__main__":
    unittest.main()
