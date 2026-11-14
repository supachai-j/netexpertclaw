"""D-13: non-Python MCP servers are deny-by-default. These tests use temporary fake servers; no such server exists in the repo."""
import pathlib, sys, tempfile, unittest
R = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / "scripts"))
import langpolicy as lp


def make(root, name, files):
    d = root / name; d.mkdir(parents=True)
    for f, t in files.items(): (d / f).write_text(t)
    return root


GOOD = {
    "go": ({"main.go": 'package main\nimport "fmt"\nfunc main(){ fmt.Println("x") }\n', "go.sum": ""}, "{root}/mcp/s/bin/s", []),
    "rust": ({"main.rs": "fn main() { println!(\"x\"); }\n", "Cargo.lock": ""}, "{root}/mcp/s/bin/s", []),
    "typescript": ({"server.ts": "import { z } from 'zod';\nexport const x = z.string();\n", "package-lock.json": "{}"}, "node", ["{root}/mcp/s/dist/server.js"]),
}


def entry(lang, cmd, args, **kw):
    e = {"language": lang, "command": cmd, "args": args, "capability": "read", "egress": [], "release_checks": ["build", "sha256", "scan"]}
    e.update(kw); return e


class Policy(unittest.TestCase):
    def check(self, lang, files=None, **kw):
        gfiles, cmd, args = GOOD[lang]
        files = gfiles if files is None else files
        cmd = kw.pop("cmd", cmd); args = kw.pop("args", args)
        with tempfile.TemporaryDirectory() as t:
            root = make(pathlib.Path(t), "s", files)
            return lp.check("s", entry(lang, cmd, args, **kw), root)

    def test_good_entries_pass(self):
        for lang in GOOD: self.assertEqual(self.check(lang), [], lang)

    def test_python_and_missing_language_are_not_checked_here(self):
        self.assertEqual(lp.check("s", {"command": "uv"}, pathlib.Path("/nonexistent")), [])
        self.assertEqual(lp.check("s", {"language": "python"}, pathlib.Path("/nonexistent")), [])

    def test_unknown_language_rejected(self):
        self.assertTrue(lp.check("s", {"language": "ruby"}, pathlib.Path("/x"))[0].startswith("server s: language 'ruby' is not allowed"))

    def test_lockfile_required(self):
        for lang in GOOD:
            files = {k: v for k, v in GOOD[lang][0].items() if k not in ("go.sum", "Cargo.lock", "package-lock.json")}
            self.assertTrue(any("lockfile" in e for e in self.check(lang, files=files)), lang)

    def test_run_at_start_commands_rejected(self):
        for cmd, args in (("npx", ["-y", "pkg"]), ("go", ["run", "."]), ("cargo", ["run"]), ("npm", ["exec", "x"]), ("bunx", ["pkg@1.0.0"]), ("/usr/bin/npx", ["pkg"]), ("npx", ["pkg@1.2.3"]), ("go", ["build"]), ("yarn", ["start"]), ("pnpm", ["dlx", "x"]), ("deno", ["run", "x.ts"])):
            for lang in GOOD:
                errs = self.check(lang, cmd=cmd, args=args)
                self.assertTrue(any("runs or installs code at start" in e for e in errs), (lang, cmd, errs))

    def test_command_must_be_built_artefact(self):
        self.assertTrue(any("command must be" in e for e in self.check("go", cmd="/usr/local/bin/anything", args=[])))
        self.assertTrue(any("command must be" in e for e in self.check("typescript", cmd="node", args=["server.js"])))
        self.assertTrue(any("command must be" in e for e in self.check("typescript", cmd="node", args=["{root}/mcp/other/dist/x.js"])))

    def test_release_checks_and_egress_declared(self):
        self.assertTrue(any("release_checks" in e for e in self.check("go", release_checks=[])))
        with tempfile.TemporaryDirectory() as t:
            root = make(pathlib.Path(t), "s", GOOD["go"][0]); e = entry("go", "{root}/mcp/s/bin/s", []); del e["egress"]
            self.assertTrue(any("declare egress" in x for x in lp.check("s", e, root)))

    def test_network_imports_need_egress(self):
        cases = {
            "go": {"main.go": 'package main\nimport (\n\t"net/http"\n)\nfunc main(){ http.Get("x") }\n', "go.sum": ""},
            "rust": {"main.rs": "use reqwest::blocking::get;\nfn main(){}\n", "Cargo.lock": ""},
            "typescript": {"server.ts": "const r = await fetch('https://example.org');\n", "package-lock.json": "{}"},
        }
        for lang, files in cases.items():
            self.assertTrue(any("network modules" in e for e in self.check(lang, files=files)), lang)
            self.assertFalse(any("network modules" in e for e in self.check(lang, files=files, egress=["example.org"])), lang)
        ts = {"server.js": "const http = require('node:https');\n", "package-lock.json": "{}"}
        self.assertTrue(any("network modules" in e for e in self.check("typescript", files=ts)))

    def test_process_spawning_rejected_even_with_egress(self):
        cases = {
            "go": {"main.go": 'package main\nimport "os/exec"\nfunc main(){ exec.Command("sh") }\n', "go.sum": ""},
            "rust": {"main.rs": "use std::process::Command;\nfn main(){ Command::new(\"sh\"); }\n", "Cargo.lock": ""},
            "typescript": {"server.ts": "import { exec } from 'child_process';\n", "package-lock.json": "{}"},
        }
        for lang, files in cases.items():
            self.assertTrue(any("spawn processes" in e for e in self.check(lang, files=files, egress=["example.org"])), lang)
        ev = {"server.ts": "const f = new Function('return 1');\n", "package-lock.json": "{}"}
        self.assertTrue(any("spawn processes" in e for e in self.check("typescript", files=ev)))

    def test_vendored_dirs_are_not_scanned(self):
        files = dict(GOOD["typescript"][0]); files["node_modules/x/index.js"] = "const http=require('http')"
        with tempfile.TemporaryDirectory() as t:
            root = make(pathlib.Path(t), "s", files if "/" not in "".join(files) else {k: v for k, v in files.items() if "/" not in k})
            nm = root / "s" / "node_modules" / "x"; nm.mkdir(parents=True); (nm / "index.js").write_text("const http=require('http')")
            self.assertEqual(lp.check("s", entry("typescript", "node", ["{root}/mcp/s/dist/server.js"]), root), [])

    def test_no_sources_rejected(self):
        files = {"go.sum": ""}
        self.assertTrue(any("no .go sources" in e for e in self.check("go", files=files)))

    def test_repo_registry_has_no_unreviewed_language(self):
        import json
        reg = json.loads((R / "mcp" / "servers.json").read_text())
        for n, e in reg.items():
            self.assertIn(e.get("language", "python"), ("python",), f"{n}: a non-Python server needs D-13 review; remove this assertion only in that PR")


if __name__ == "__main__":
    unittest.main()
