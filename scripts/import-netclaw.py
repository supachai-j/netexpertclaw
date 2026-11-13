#!/usr/bin/env python3
"""Import reviewed NetClaw skills at a pinned commit (see docs/SECURITY-REVIEW.md, section E).

Reads imports/netclaw.json. For each listed skill: verifies the upstream checkout is at the pinned commit,
takes ONLY SKILL.md (no scripts/binaries/symlinks), applies exact-match text replacements from the manifest
(fails if a replacement does not match -> upstream drifted), rewrites frontmatter to our schema, records the
upstream file sha256 + a NOTICE entry, and registers the external MCP server pinned to a commit + hashed
requirements file in mcp/servers.json. Output is deterministic; re-running yields no diff.

Usage: import-netclaw.py [--upstream DIR]   (default: shallow-fetch the pinned commit into a temp dir)
"""
import argparse, hashlib, json, pathlib, re, subprocess, sys, tempfile
from common import ROOT, split, parse_fm

MANIFEST = ROOT / "imports" / "netclaw.json"
MARK = "<!-- netexpertclaw:imported-from-netclaw -->"


def sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()


def checkout(commit: str, repo: str, given: str | None) -> pathlib.Path:
    if given:
        d = pathlib.Path(given)
    else:
        d = pathlib.Path(tempfile.mkdtemp(prefix="nc-")) / "up"
        subprocess.run(["git", "init", "-q", str(d)], check=True)
        subprocess.run(["git", "-C", str(d), "fetch", "-q", "--depth", "1", repo, commit], check=True)
        subprocess.run(["git", "-C", str(d), "checkout", "-q", "FETCH_HEAD"], check=True)
    head = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    if head != commit:
        sys.exit(f"upstream HEAD {head} != pinned {commit}")
    return d


def transform(up_text: str, s: dict) -> tuple[str, str]:
    fm, body = split(up_text)
    m = parse_fm(fm)
    for old, new in s.get("replace", []):
        if old not in body:
            sys.exit(f"{s['name']}: replacement target not found (upstream drifted?): {old[:60]!r}")
        body = body.replace(old, new)
    ver = m.get("version", "0.0.0")
    desc = m["description"].replace('"', "'")
    out = (f"---\nname: {s['name']}\ndescription: {desc}\nlicense: {m.get('license', 'Apache-2.0')}\nmetadata:\n"
           f"  version: \"{ver}\"\n  risk: {s['risk']}\n  mcp_servers: \"{s['mcp_server']}\"\n  requires_bins: \"{s['requires_bins']}\"\n---\n"
           f"{MARK}\n{body.lstrip(chr(10))}")
    return out, ver


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--upstream"); a = ap.parse_args()
    man = json.loads(MANIFEST.read_text())
    up = checkout(man["upstream"]["commit"], man["upstream"]["repo"], a.upstream)
    notice = (ROOT / "NOTICE").read_text()
    head, _, _ = notice.partition("\nImported by scripts/import-netclaw.py")
    entries = []
    for s in man["skills"]:
        src = up / s["upstream_path"]
        if src.is_symlink() or not src.is_file(): sys.exit(f"{s['name']}: upstream file missing or symlink")
        raw = src.read_bytes()
        text, ver = transform(raw.decode(), s)
        d = ROOT / "skills" / s["name"]; d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(text)
        entries.append(f"- {s['upstream_path']} (sha256 {sha(raw)[:16]}...) -> skills/{s['name']}/SKILL.md | modified: yes (frontmatter rewritten, {len(s.get('replace', []))} text replacement(s))")
        print("imported", s["name"], "upstream version", ver)
    servers = json.loads((ROOT / "mcp" / "servers.json").read_text())
    for name, e in man["external_mcp"].items():
        req = ROOT / e["requirements"]
        if sha(req.read_bytes()) != e["requirements_sha256"]: sys.exit(f"{name}: requirements file hash mismatch")
        child = ["uv", "run", "--quiet", "--no-project", "--isolated", "--with-requirements", "{root}/" + e["requirements"],
                 "--with", f"git+{e['git']}@{e['commit']}", "python", "{root}/" + e["launcher"]]
        if e.get("lazy_proxy"):
            servers[name] = {"command": "python3", "capability": e["capability"], "env": {},
                             "args": ["{root}/" + e["lazy_proxy"], "--cache", "{root}/" + e["tools_cache"], "--"] + child}
        else:
            servers[name] = {"command": "uv", "capability": e["capability"], "env": {}, "args": child[1:]}
    (ROOT / "mcp" / "servers.json").write_text(json.dumps(servers, indent=2) + "\n")
    block = ("\nImported by scripts/import-netclaw.py from commit " + man["upstream"]["commit"] + " (Apache-2.0):\n" + "\n".join(entries) + "\n")
    (ROOT / "NOTICE").write_text(head.rstrip("\n") + "\n" + block)
    return 0

if __name__ == "__main__":
    sys.exit(main())
