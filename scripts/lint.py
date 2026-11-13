#!/usr/bin/env python3
"""Lint canonical skills + MCP registry. Exit 1 on any problem."""
import re, sys
from common import ROOT, REQUIRED, META_REQUIRED, RISKS, skills, servers

SECRET = re.compile(r"(?i)(password|secret|token|api[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}")

def main() -> int:
    errs = []
    srv = servers()
    for s in skills():
        m, d = s["meta"], s["dir"]
        for k in REQUIRED:
            if not m.get(k): errs.append(f"{d.name}: missing {k}")
        if m.get("name") != d.name: errs.append(f"{d.name}: name != directory")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", m.get("name", "")): errs.append(f"{d.name}: bad name")
        if len(m.get("description", "")) > 1024: errs.append(f"{d.name}: description >1024")
        meta = m.get("metadata") or {}
        for k in META_REQUIRED:
            if not meta.get(k): errs.append(f"{d.name}: metadata.{k} missing")
        if meta.get("risk") not in RISKS: errs.append(f"{d.name}: risk must be read|write")
        for name in filter(None, (meta.get("mcp_servers") or "").split(",")):
            if name.strip() not in srv: errs.append(f"{d.name}: unknown mcp server {name.strip()}")
        if meta.get("risk") == "write" and "approval" not in s["body"].lower():
            errs.append(f"{d.name}: write skill must document an approval step")
        if SECRET.search(s["text"]): errs.append(f"{d.name}: possible secret in SKILL.md")
    for p in ROOT.rglob("*"):
        if p.is_file() and ".git" not in p.parts and "dist" not in p.parts and p.suffix in {".py", ".json", ".md", ".toml", ".yaml"}:
            if p.name != "lint.py" and SECRET.search(p.read_text(errors="ignore")):
                errs.append(f"{p.relative_to(ROOT)}: possible secret")
    print("\n".join(errs) or f"lint ok ({len(skills())} skill(s), {len(srv)} server(s))")
    return 1 if errs else 0

if __name__ == "__main__":
    sys.exit(main())
