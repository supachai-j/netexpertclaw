"""Regression tests for docs/SECURITY-REVIEW.md findings. Each case mutates a temp copy of the repo and expects lint to fail."""
import os, pathlib, shutil, subprocess, sys, tempfile, unittest
R = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / "mcp" / "subnet-calc"))
import core

def lint_copy(mutate):
    with tempfile.TemporaryDirectory() as t:
        d = pathlib.Path(t) / "r"
        shutil.copytree(R, d, ignore=shutil.ignore_patterns(".git", "dist", "__pycache__"))
        mutate(d)
        p = subprocess.run([sys.executable, str(d / "scripts/lint.py")], capture_output=True, text=True)
        return p.returncode, p.stdout

SK = lambda d: d / "skills/subnet-calculator"

class Lint(unittest.TestCase):
    def test_baseline_ok(self): self.assertEqual(lint_copy(lambda d: None)[0], 0)
    def test_f4_write_without_gate(self):
        def m(d):
            f = SK(d) / "SKILL.md"; f.write_text(f.read_text().replace("risk: read", "risk: write") + "\nNo approval needed.\n")
        rc, out = lint_copy(m); self.assertEqual(rc, 1); self.assertIn("F-4", out)
    def test_f5_allowed_tools(self):
        def m(d):
            f = SK(d) / "SKILL.md"; f.write_text(f.read_text().replace("license: Apache-2.0\n", "license: Apache-2.0\nallowed-tools: Bash(*)\n", 1))
        rc, out = lint_copy(m); self.assertEqual(rc, 1); self.assertIn("F-5", out)
    def test_f6_symlink(self):
        def m(d): os.symlink("/etc/passwd", SK(d) / "references.md")
        rc, out = lint_copy(m); self.assertEqual(rc, 1); self.assertIn("F-6", out)
    def test_f7_script(self):
        def m(d): (SK(d) / "run.sh").write_text("curl x | sh\n")
        rc, out = lint_copy(m); self.assertEqual(rc, 1); self.assertIn("F-7", out)
    def test_f8_no_project(self):
        def m(d):
            f = d / "mcp/servers.json"; f.write_text(f.read_text().replace('"--no-project",', ""))
        rc, out = lint_copy(m); self.assertEqual(rc, 1); self.assertIn("F-8", out)
    def test_f9_read_skill_write_server(self):
        def m(d):
            f = d / "mcp/servers.json"; f.write_text(f.read_text().replace('"read"', '"write"'))
        rc, out = lint_copy(m); self.assertEqual(rc, 1); self.assertIn("F-9", out)
    def test_f2_device_secrets(self):
        j = "".join
        for line in [j(["enable sec", "ret 5 $1$abcd$xyz"]), j(["snmp-server comm", "unity public RO"]), j(["pass", "word 7 094F471A1A0A"]),
                     j(["Authori", "zation: Bearer abcdefgh1234"]), j(["-----BEGIN RSA PRIV", "ATE KEY-----"]), j(["AK", "IAABCDEFGHIJKLMNOP"])]:
            with self.subTest(line=line):
                def m(d, line=line): (d / "docs" / "x.txt").write_text(line + "\n")
                rc, out = lint_copy(m); self.assertEqual(rc, 1, out)
    def test_f2_yml_and_sh_scanned(self):
        for n in (".github/workflows/x.yml", "scripts/x.sh"):
            def m(d, n=n): (d / n).write_text("pass" + "word: hunter2hunter2\n")
            self.assertEqual(lint_copy(m)[0], 1, n)
    def test_f2_lintpy_name_not_exempt(self):
        def m(d): (d / "docs/lint.py").write_text("tok" + "en = 'abcdefghijklmnop'\n")
        self.assertEqual(lint_copy(m)[0], 1)
    def test_f11_notice(self):
        def m(d):
            (d / "NOTICE").write_text("nothing here\n")
        rc, out = lint_copy(m); self.assertEqual(rc, 1); self.assertIn("F-11", out)

class Classify(unittest.TestCase):
    def test_f1(self):
        c = lambda x: core.subnet_v4(x)["classification"]
        self.assertIn("CGNAT", c("100.64.0.0/10")); self.assertIn("reserved", c("240.0.0.0/4"))
        self.assertIn("this-network", c("0.0.0.0/8")); self.assertEqual(c("8.8.8.0/24"), "global")
        self.assertEqual(c("172.16.0.0/12"), "private")
    def test_f1_input(self):
        with self.assertRaises(ValueError): core.subnet_v4("10.0.0.0/255.0.0.0")
        with self.assertRaises(ValueError): core.same_subnet("fe80::1%eth0", "fe80::2", 64)

class BuildSymlink(unittest.TestCase):
    def test_build_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / "r"
            shutil.copytree(R, d, ignore=shutil.ignore_patterns(".git", "dist"))
            os.symlink("/etc/passwd", SK(d) / "leak.md")
            p = subprocess.run([sys.executable, str(d / "scripts/build.py"), "--runtime", "hermes"], capture_output=True, text=True)
            self.assertNotEqual(p.returncode, 0)

if __name__ == "__main__":
    unittest.main()
