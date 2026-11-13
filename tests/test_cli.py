import os, pathlib, subprocess, sys, tempfile, unittest
R = pathlib.Path(__file__).resolve().parent.parent
NXC = [sys.executable, str(R / "bin" / "nxc")]

def run(*a, home=None):
    env = dict(os.environ, HOME=home or os.environ["HOME"])
    return subprocess.run(NXC + list(a), capture_output=True, text=True, env=env)

class Cli(unittest.TestCase):
    def test_version_list_lint(self):
        self.assertIn("nxc 0.1.0", run("version").stdout)
        out = run("list").stdout; self.assertIn("subnet-calculator", out); self.assertIn("fwrule-analyzer", out)
        self.assertEqual(run("lint").returncode, 0)
    def test_install_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            p = run("install", "hermes", "--root", "/opt/x", home=t)
            self.assertEqual(p.returncode, 0, p.stderr); self.assertIn("dry run", p.stdout)
            self.assertFalse((pathlib.Path(t) / ".hermes").exists())
    def test_install_apply_copies_skills_not_config_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(run("install", "hermes", "--apply", "--root", "/opt/x", home=t).returncode, 0)
            base = pathlib.Path(t) / ".hermes" / "skills" / "netexpertclaw"
            self.assertTrue((base / "subnet-calculator" / "SKILL.md").exists())
            self.assertFalse((pathlib.Path(t) / ".hermes" / "config.yaml").exists())
            self.assertIn("skip", run("install", "hermes", "--apply", "--root", "/opt/x", home=t).stdout)
    def test_bad_runtime(self):
        self.assertNotEqual(run("install", "nope").returncode, 0)

if __name__ == "__main__":
    unittest.main()
