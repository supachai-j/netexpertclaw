"""Agent Skills best-practice gates (agentskills.io spec + creator guides) enforced by scripts/lint.py; each case mutates a temp copy of the repo."""
import json, os, pathlib, re, shutil, subprocess, sys, tempfile, unittest
R = pathlib.Path(__file__).resolve().parent.parent

def lint_copy(mutate):
    with tempfile.TemporaryDirectory() as t:
        d = pathlib.Path(t) / "r"
        shutil.copytree(R, d, ignore=shutil.ignore_patterns(".git", "dist", "__pycache__"))
        mutate(d)
        p = subprocess.run([sys.executable, str(d / "scripts/lint.py")], capture_output=True, text=True)
        return p.returncode, p.stdout

SK = lambda d, n="rfc-lookup": d / "skills" / n

def edit(path, fn): path.write_text(fn(path.read_text()))

class Quality(unittest.TestCase):
    def test_baseline(self): self.assertEqual(lint_copy(lambda d: None)[0], 0)
    def test_description_must_say_when(self):
        rc, out = lint_copy(lambda d: edit(SK(d) / "SKILL.md", lambda s: re.sub(r"(?m)^description: .*$", "description: Looks up RFCs.", s, 1)))
        self.assertEqual(rc, 1); self.assertIn("Use this skill when", out)
    def test_description_length(self):
        rc, out = lint_copy(lambda d: edit(SK(d) / "SKILL.md", lambda s: re.sub(r"(?m)^description: (.*)$", lambda m: "description: " + m.group(1) + " x" * 600, s, 1)))
        self.assertEqual(rc, 1); self.assertIn("description >1024", out)
    def test_compatibility_required(self):
        rc, out = lint_copy(lambda d: edit(SK(d) / "SKILL.md", lambda s: re.sub(r"(?m)^compatibility: .*\n", "", s, 1)))
        self.assertEqual(rc, 1); self.assertIn("compatibility", out)
    def test_gotchas_required(self):
        rc, out = lint_copy(lambda d: edit(SK(d) / "SKILL.md", lambda s: s.replace("## Gotchas", "## Notes")))
        self.assertEqual(rc, 1); self.assertIn("Gotchas", out)
    def test_body_size_limit(self):
        rc, out = lint_copy(lambda d: edit(SK(d) / "SKILL.md", lambda s: s + "\nfiller line\n" * 520))
        self.assertEqual(rc, 1); self.assertIn("too long", out)
    def test_spec_name_rules(self):
        def m(d):
            old = SK(d); new = d / "skills" / "bad--name"; old.rename(new)
            edit(new / "SKILL.md", lambda s: s.replace("name: rfc-lookup", "name: bad--name", 1))
        rc, out = lint_copy(m); self.assertEqual(rc, 1); self.assertIn("bad name", out)
    def test_yaml_colon_in_scalar(self):
        rc, out = lint_copy(lambda d: edit(SK(d) / "SKILL.md", lambda s: re.sub(r"(?m)^compatibility: ", "compatibility: Offline: ", s, 1)))
        self.assertEqual(rc, 1); self.assertIn("unquoted YAML", out)
    def test_trigger_evals_required(self):
        rc, out = lint_copy(lambda d: (SK(d) / "evals" / "trigger_queries.json").unlink())
        self.assertEqual(rc, 1); self.assertIn("trigger_queries.json", out)
    def test_trigger_evals_need_both_splits_and_labels(self):
        def m(d):
            f = SK(d) / "evals" / "trigger_queries.json"; q = json.loads(f.read_text())
            f.write_text(json.dumps([x for x in q if x["should_trigger"] or x["split"] == "train"]))   # drop validation negatives
        rc, out = lint_copy(m); self.assertEqual(rc, 1); self.assertIn("validation", out)
    def test_output_evals_need_assertions(self):
        def m(d):
            f = SK(d) / "evals" / "evals.json"; e = json.loads(f.read_text()); e["evals"][0]["assertions"] = []; f.write_text(json.dumps(e))
        rc, out = lint_copy(m); self.assertEqual(rc, 1); self.assertIn("assertions", out)
    def test_tool_lock_required(self):
        rc, out = lint_copy(lambda d: (d / "mcp" / "rfc-lookup" / "tools.lock.json").unlink())
        self.assertEqual(rc, 1); self.assertIn("pinned tool definitions", out)
    def test_evals_not_shipped_in_dist(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / "r"; shutil.copytree(R, d, ignore=shutil.ignore_patterns(".git", "dist", "__pycache__"))
            subprocess.run([sys.executable, str(d / "scripts/build.py"), "--runtime", "codex"], check=True, capture_output=True)
            self.assertTrue((d / "dist/codex/skills/rfc-lookup/SKILL.md").exists())
            self.assertFalse(list((d / "dist").rglob("evals")))

class Evals(unittest.TestCase):
    def test_every_skill_has_balanced_queries(self):
        for sk in (R / "skills").iterdir():
            q = json.loads((sk / "evals/trigger_queries.json").read_text())
            self.assertGreaterEqual(sum(x["should_trigger"] for x in q), 8, sk.name)
            self.assertGreaterEqual(sum(not x["should_trigger"] for x in q), 8, sk.name)
            self.assertEqual(len({x["query"] for x in q}), len(q), f"{sk.name}: duplicate queries")
    def test_no_customer_like_data_in_eval_queries(self):
        bad = re.compile(r"\b(?!0\.|255\.|10\.|172\.(1[6-9]|2\d|3[01])\.|192\.168\.|192\.0\.2\.|198\.51\.100\.|203\.0\.113\.)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
        for f in (R / "skills").glob("*/evals/*.json"):
            self.assertFalse(bad.search(f.read_text()), f"{f}: non-documentation public IP in eval data")

if __name__ == "__main__":
    unittest.main()
