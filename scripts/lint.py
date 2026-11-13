#!/usr/bin/env python3
"""Lint canonical skills + MCP registry. Exit 1 on any problem. Findings F-2..F-11 of docs/SECURITY-REVIEW.md."""
import json, pathlib, re, sys
from common import ROOT, REQUIRED, META_REQUIRED, RISKS, skills, servers, parse_fm

ALLOWED_TOP = {"name", "description", "license", "metadata", "compatibility"}
ALLOWED_FILES = re.compile(r"^(SKILL\.md|references/[^/]+\.md|agents/[^/]+\.yaml)$")
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


def main() -> int:
    errs = []
    srv = servers()
    for n, e in srv.items():
        if e.get("capability") not in ("read", "write"): errs.append(f"server {n}: capability must be read|write")
        a = e.get("args", [])
        if e.get("command") == "uv":
            pinned = any(x.startswith("mcp==") for x in a) or ("--with-requirements" in a and any(re.search(r"^git\+\S+@[0-9a-f]{40}$", x) for x in a))
            if "--no-project" not in a or "--isolated" not in a or not pinned:
                errs.append(f"server {n}: uv run needs --no-project --isolated and exact pins (== or requirements + git@sha) (F-8/F-10)")
    for s in skills():
        m, d = s["meta"], s["dir"]
        for k in REQUIRED:
            if not m.get(k): errs.append(f"{d.name}: missing {k}")
        for k in m:
            if k not in ALLOWED_TOP: errs.append(f"{d.name}: frontmatter key '{k}' not allowed (F-5)")
        if m.get("name") != d.name: errs.append(f"{d.name}: name != directory")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", m.get("name", "")): errs.append(f"{d.name}: bad name")
        if len(m.get("description", "")) > 1024: errs.append(f"{d.name}: description >1024")
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
