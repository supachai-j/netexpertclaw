"""Language policy for MCP servers (docs/DECISIONS.md D-13). Deny by default.

Python (stdlib + pinned `mcp`) is the default and is checked in lint.py. Go, Rust and TypeScript servers are allowed only when the
registry entry declares `language` and all of these hold (checked here, statically):
  - a committed lockfile (go.sum | Cargo.lock | package-lock.json) next to the sources;
  - the command is a built artefact under mcp/<name>/ (Go/Rust binary, or `node` + a built .js file), never go run, cargo run,
    npx, bunx, pnpm dlx, deno run or an install-on-start command;
  - explicit `egress`; source imports of network modules need a non-empty `egress`;
  - the source does not spawn processes (os/exec, std::process, child_process);
  - `release_checks` lists the CI jobs that build it reproducibly, hash the artefact and scan it (reviewed by a person).
Static scans are a tripwire, not a proof: reviewers still read the code.
"""
import re

LANGS = {
    "go": {"ext": (".go",), "lock": "go.sum",
           "net": r'"(net|net/http|net/rpc|crypto/tls|golang\.org/x/net[^"]*|google\.golang\.org/grpc[^"]*|github\.com/(gorilla/websocket|go-resty/resty)[^"]*)"',
           "proc": r'"(os/exec|syscall)"|\bexec\.Command\w*\('},
    "rust": {"ext": (".rs",), "lock": "Cargo.lock",
             "net": r"\b(std::net|tokio::net|reqwest|hyper|ureq|isahc|surf|tonic|tungstenite|socket2|curl)\b",
             "proc": r"\b(std::process|tokio::process|Command::new)\b"},
    "typescript": {"ext": (".ts", ".js", ".mjs", ".cjs", ".mts"), "lock": "package-lock.json",
                   "net": r"""(?:from\s+|require\()\s*['"](?:node:)?(?:http|https|http2|net|tls|dgram|dns|undici|axios|got|node-fetch|ws|superagent|request)['"]|\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\b""",
                   "proc": r"""(?:from\s+|require\()\s*['"](?:node:)?(?:child_process|worker_threads|cluster)['"]|\beval\s*\(|\bnew\s+Function\s*\("""},
}
BANNED_CMD = re.compile(r"(^|/)(npx|bunx|pnpx|pnpm|yarn|deno|go|cargo|npm|bun)$")
BANNED_ARGS = {"run", "dlx", "exec", "install", "x", "-y", "--yes", "-p"}
SKIP = {"node_modules", "target", "vendor", ".git", "dist", "bin", "build"}


def sources(d, lang):
    exts = LANGS[lang]["ext"]
    return [p for p in d.rglob("*") if p.is_file() and p.suffix in exts and not (SKIP & set(p.relative_to(d).parts))]


def scan(d, lang):
    """Return (files importing network modules, files spawning processes)."""
    net, proc = [], []
    for p in sources(d, lang):
        t = p.read_text(errors="replace")
        if re.search(LANGS[lang]["net"], t): net.append(p.name)
        if re.search(LANGS[lang]["proc"], t): proc.append(p.name)
    return net, proc


def check(name, entry, mcp_dir):
    """Errors for one registry entry that declares a non-Python language."""
    lang = entry.get("language")
    if lang is None: return []
    if lang == "python": return []
    errs = []
    pre = f"server {name}: language {lang!r}"
    if lang not in LANGS: return [f"{pre} is not allowed (python, go, rust, typescript; see D-13)"]
    d = mcp_dir / name
    if not (d.is_dir() and sources(d, lang)): errs.append(f"{pre}: no {'/'.join(LANGS[lang]['ext'])} sources in mcp/{name}/")
    if not (d / LANGS[lang]["lock"]).exists(): errs.append(f"{pre}: committed lockfile {LANGS[lang]['lock']} required (pinned dependencies)")
    cmd, args = str(entry.get("command", "")), [str(a) for a in entry.get("args", [])]
    if BANNED_CMD.search(cmd) or (any(a in BANNED_ARGS for a in args) and not cmd.startswith("{root}/")):
        errs.append(f"{pre}: command {cmd!r} runs or installs code at start (npx/go run/cargo run/npm...); use a built artefact under mcp/{name}/")
    ok_cmd = cmd == f"{{root}}/mcp/{name}/bin/{name}" if lang in ("go", "rust") else (cmd == "node" and args and args[0].startswith(f"{{root}}/mcp/{name}/dist/"))
    if not ok_cmd: errs.append(f"{pre}: command must be {{root}}/mcp/{name}/bin/{name}" if lang != "typescript" else f"{pre}: command must be node with a built file under {{root}}/mcp/{name}/dist/")
    if not entry.get("release_checks"): errs.append(f"{pre}: declare `release_checks` (CI jobs that build, hash and scan the artefact)")
    if "egress" not in entry: errs.append(f"{pre}: declare egress explicitly (use [] for none)")
    if d.is_dir() and lang in LANGS:
        net, proc = scan(d, lang)
        if net and not entry.get("egress"): errs.append(f"{pre}: {', '.join(sorted(set(net)))} use network modules but egress is []")
        if proc: errs.append(f"{pre}: {', '.join(sorted(set(proc)))} spawn processes or evaluate code (not allowed for servers)")
    return errs
