#!/usr/bin/env python3
"""Lint canonical skills + MCP registry. Exit 1 on any problem. Findings F-2..F-11 of docs/SECURITY-REVIEW.md."""
import json, pathlib, re, sys
from common import ROOT, REQUIRED, META_REQUIRED, RISKS, skills, servers, parse_fm

ALLOWED_TOP = {"name", "description", "license", "metadata", "compatibility"}
ALLOWED_FILES = re.compile(r"^(SKILL\.md|references/[^/]+\.md|agents/[^/]+\.yaml|evals/(evals|trigger_queries)\.json)$")
SECRET = [re.compile(p) for p in (
    r"(?i)(password|passwd|secret|token|api[_-]?key|community)\s*[:=]\s*['\"]?[^\s'\"]{6,}",
    r"(?i)\b(enable\s+)?(secret|password)\s+[0-9]\s+\S{4,}",           # Cisco type 0-9
    r"(?i)snmp-server\s+community\s+\S+",
    r"(?i)authorization:\s*(bearer|basic)\s+\S{8,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"\bAKIA[0-9A-Z]{16}\b", r"\bgh[pousr]_[A-Za-z0-9]{30,}\b",
    r"://[^/\s:@]+:[^/\s@]+@",                                           # creds in URL
)]
TEXT_SUFFIX = {".py", ".json", ".md", ".toml", ".yaml", ".yml", ".sh", ".txt", ".ini", ".cfg", ".env", ".js", ".cfg"}
SKIP_SECRET = {"scripts/lint.py", "docs/SECURITY-REVIEW.md"}  # exact paths only
SKIP_DIRS = {".git", "dist", "__pycache__", "security-evidence"}


def eval_files(d: pathlib.Path) -> list[str]:
    """agentskills.io 'Optimizing descriptions' / 'Evaluating skills': trigger queries (>=8 each way, train+validation) and output evals with assertions."""
    out, tq, ev = [], d / "evals" / "trigger_queries.json", d / "evals" / "evals.json"
    try:
        q = json.loads(tq.read_text())
        for label in (True, False):
            for sp in ("train", "validation"):
                n = sum(1 for x in q if x.get("should_trigger") is label and x.get("split") == sp)
                if n < 3: out.append(f"{d.name}/evals/trigger_queries.json: need >=3 should_trigger={label} queries in {sp} (have {n})")
            if sum(1 for x in q if x.get("should_trigger") is label) < 8: out.append(f"{d.name}/evals/trigger_queries.json: need >=8 should_trigger={label} queries")
        if any(not x.get("query") or x.get("split") not in ("train", "validation") for x in q): out.append(f"{d.name}/evals/trigger_queries.json: every item needs query + split train|validation")
    except (OSError, ValueError): out.append(f"{d.name}/evals/trigger_queries.json missing or invalid")
    try:
        e = json.loads(ev.read_text())
        if e.get("skill_name") != d.name or len(e.get("evals", [])) < 2: out.append(f"{d.name}/evals/evals.json: skill_name must match and >=2 evals")
        for c in e.get("evals", []):
            if not (c.get("prompt") and c.get("expected_output") and isinstance(c.get("assertions"), list) and c["assertions"]): out.append(f"{d.name}/evals/evals.json: eval {c.get('id')} needs prompt, expected_output, assertions[]")
    except (OSError, ValueError): out.append(f"{d.name}/evals/evals.json missing or invalid")
    return out


def main() -> int:
    errs = []
    srv = servers()
    for n, e in srv.items():
        if e.get("capability") not in ("read", "write"): errs.append(f"server {n}: capability must be read|write")
        eg = e.get("egress", [])
        if not isinstance(eg, list) or not all(isinstance(h, str) and re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", h) for h in eg):
            errs.append(f"server {n}: egress must be a list of hostnames")
        a = e.get("args", [])
        cmd, ca = e.get("command"), a
        if cmd == "python3" and a and a[0].endswith("/mcp/" + n + "/proxy.py") and "--" in a:
            cmd, ca = a[a.index("--") + 1], a[a.index("--") + 2:]   # lint the real child command behind the lazy proxy
            cache = ROOT / "mcp" / n / "tools.cache.json"
            if not cache.exists(): errs.append(f"server {n}: proxy needs {cache.name}")
        if cmd == "uv":
            pinned = any(x.startswith("mcp==") for x in ca) or ("--with-requirements" in ca and any(re.search(r"^git\+\S+@[0-9a-f]{40}$", x) for x in ca))
            if "--no-project" not in ca or "--isolated" not in ca or not pinned:
                errs.append(f"server {n}: uv run needs --no-project --isolated and exact pins (== or requirements + git@sha) (F-8/F-10)")
    for n in srv:
        if not any((ROOT / "mcp" / n / f).exists() for f in ("tools.lock.json", "tools.cache.json")):
            errs.append(f"server {n}: no pinned tool definitions (run scripts/gen_tools_cache.py {n}) - rug-pull detection")
    for s in skills():
        m, d = s["meta"], s["dir"]
        for k in REQUIRED:
            if not m.get(k): errs.append(f"{d.name}: missing {k}")
        for k in m:
            if k not in ALLOWED_TOP: errs.append(f"{d.name}: frontmatter key '{k}' not allowed (F-5)")
        if m.get("name") != d.name: errs.append(f"{d.name}: name != directory")
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", m.get("name", "")) or len(m.get("name", "")) > 64:
            errs.append(f"{d.name}: bad name (agentskills.io: <=64 chars, [a-z0-9-], no leading/trailing/double hyphen)")
        desc = m.get("description", "")
        if len(desc) > 1024: errs.append(f"{d.name}: description >1024")
        if not re.search(r"\bUse (this skill )?(when|whenever)\b", desc):
            errs.append(f"{d.name}: description must say when to use it ('Use this skill when ...') - it is the only trigger signal")
        for fld in ("description", "compatibility"):
            if re.search(r": |\s#", m.get(fld, "")) and not m.get(fld, "").startswith(("'", '"')):
                errs.append(f"{d.name}: {fld} contains ': ' or ' #' in an unquoted YAML scalar (official skills-ref validator rejects it)")
        comp = m.get("compatibility", "")
        if not comp or len(comp) > 500: errs.append(f"{d.name}: compatibility (<=500 chars: requirements, network access) is required")
        nlines = s["body"].count("\n") + 1
        if nlines > 500 or len(s["text"]) / 4 > 5000: errs.append(f"{d.name}: SKILL.md too long ({nlines} lines, ~{len(s['text']) // 4} tokens; limit 500 lines / 5000 tokens, move detail to references/)")
        if not re.search(r"(?m)^## Gotchas\s*$", s["body"]): errs.append(f"{d.name}: needs a '## Gotchas' section (concrete, verified corrections)")
        errs += eval_files(d)
        meta = m.get("metadata") or {}
        for k in META_REQUIRED:
            if not meta.get(k): errs.append(f"{d.name}: metadata.{k} missing")
        risk = meta.get("risk")
        if risk not in RISKS: errs.append(f"{d.name}: risk must be read|write")
        for name in filter(None, (x.strip() for x in (meta.get("mcp_servers") or "").split(","))):
            if name not in srv: errs.append(f"{d.name}: unknown mcp server {name}")
            elif risk == "read" and srv[name].get("capability") == "write":
                errs.append(f"{d.name}: risk=read skill uses write-capable server {name} (F-9)")
        if risk == "write":
            if meta.get("approval") != "required" or not re.search(r"(?m)^## Approval\s*$", s["body"]):
                errs.append(f"{d.name}: write skill needs metadata.approval=required and a '## Approval' section (F-4)")
        for p in d.rglob("*"):
            rel = p.relative_to(d).as_posix()
            if p.is_symlink(): errs.append(f"{d.name}/{rel}: symlink not allowed (F-6)")
            elif p.is_file() and not ALLOWED_FILES.match(rel): errs.append(f"{d.name}/{rel}: file type/path not allow-listed (F-7)")
        if re.search(r"(?i)netclaw", s["text"]) and d.name not in (ROOT / "NOTICE").read_text():
            errs.append(f"{d.name}: mentions NetClaw but has no NOTICE entry (F-11)")
    names = {s["dir"].name for s in skills()}
    prof = json.loads((ROOT / "profiles.json").read_text())
    for pn, v in prof.items():
        if v != "*" and not set(v) <= names: errs.append(f"profiles.json: {pn} references unknown skill {sorted(set(v) - names)}")
    if not (ROOT / "LICENSE").exists(): errs.append("LICENSE missing (F-11)")
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT).as_posix()
        if p.is_symlink() or not p.is_file() or set(p.relative_to(ROOT).parts) & SKIP_DIRS or rel in SKIP_SECRET:
            continue
        if p.suffix in TEXT_SUFFIX or p.name.startswith(".env") or p.name in {"Dockerfile", "NOTICE", "LICENSE"}:
            t = p.read_text(errors="ignore")
            if p.name == "LICENSE": continue
            for rx in SECRET:
                if rx.search(t): errs.append(f"{rel}: possible secret ({rx.pattern[:30]}...)"); break
    print("\n".join(errs) or f"lint ok ({len(skills())} skill(s), {len(srv)} server(s))")
    return 1 if errs else 0

if __name__ == "__main__":
    sys.exit(main())
