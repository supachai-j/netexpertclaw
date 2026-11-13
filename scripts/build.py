#!/usr/bin/env python3
"""Render per-runtime artifacts from canonical skills/ + mcp/servers.json into dist/<runtime>/.
Usage: build.py [--runtime all|claude-code|codex|hermes|openclaw|thclaws] [--root /install/path]
Claude Code: also (re)writes ./.mcp.json (uses ${CLAUDE_PLUGIN_ROOT}).
"""
import argparse, json, shutil, sys
from common import ROOT, skills, servers

DIST = ROOT / "dist"


def mcp_entry(e: dict, root: str) -> dict:
    return {**e, "args": [a.replace("{root}", root) for a in e["args"]]}


def copy_skill(s, dest):
    if dest.exists(): shutil.rmtree(dest)
    shutil.copytree(s["dir"], dest)


def claude_code():
    srv = {k: mcp_entry(v, "${CLAUDE_PLUGIN_ROOT}") for k, v in servers().items()}
    (ROOT / ".mcp.json").write_text(json.dumps({"mcpServers": srv}, indent=2) + "\n")


def thclaws(root):
    out = DIST / "thclaws" / ".thclaws"
    for s in skills(): copy_skill(s, out / "skills" / s["dir"].name)
    srv = {k: mcp_entry(v, root) for k, v in servers().items()}
    (out / "mcp.json").write_text(json.dumps({"mcpServers": srv}, indent=2) + "\n")


def codex(root):
    out = DIST / "codex"
    for s in skills():
        d = out / "skills" / s["dir"].name
        copy_skill(s, d)
        deps = [x.strip() for x in (s["meta"].get("metadata", {}).get("mcp_servers") or "").split(",") if x.strip()]
        y = ["policy:", "  allow_implicit_invocation: %s" % ("true" if s["meta"]["metadata"]["risk"] == "read" else "false")]
        if deps:
            y += ["dependencies:", "  tools:"]
            for n in deps: y += ["    - type: \"mcp\"", f"      value: \"{n}\""]
        (d / "agents").mkdir(exist_ok=True)
        (d / "agents" / "openai.yaml").write_text("\n".join(y) + "\n")
    t = []
    for k, v in servers().items():
        e = mcp_entry(v, root)
        t += [f"[mcp_servers.{k}]", f'command = "{e["command"]}"', "args = " + json.dumps(e["args"]), ""]
    (out / "config.toml.snippet").write_text("\n".join(t))


def hermes(root):
    out = DIST / "hermes"
    for s in skills(): copy_skill(s, out / "skills" / "netexpertclaw" / s["dir"].name)
    y = ["mcp_servers:"]
    for k, v in servers().items():
        e = mcp_entry(v, root)
        y += [f"  {k}:", f"    command: {e['command']}", "    args:"] + [f"      - {json.dumps(a)}" for a in e["args"]]
    (out / "mcp_servers.yaml.snippet").write_text("\n".join(y) + "\n")


def openclaw(root):
    out = DIST / "openclaw"
    for s in skills():
        d = out / "skills" / s["dir"].name
        copy_skill(s, d)
        m = s["meta"].get("metadata", {})
        bins = [b for b in (m.get("requires_bins") or "").split(",") if b]
        oc = json.dumps({"openclaw": {"requires": {"bins": bins}}})
        fm = "\n".join(l for l in s["fm"].splitlines()
                       if not l.startswith("metadata:") and not l.startswith("  "))
        fm += f"\nmetadata: {oc}\nversion: {m.get('version', '0.0.0')}"
        (d / "SKILL.md").write_text(f"---\n{fm}\n---\n{s['body']}")
    srv = {k: mcp_entry(v, root) for k, v in servers().items()}
    (out / "mcp.json.snippet").write_text(json.dumps({"mcpServers": srv}, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime", default="all")
    ap.add_argument("--root", default="/opt/netexpertclaw", help="install path of this repo on the target machine")
    a = ap.parse_args()
    targets = {"claude-code": lambda: claude_code(), "codex": lambda: codex(a.root), "hermes": lambda: hermes(a.root),
               "openclaw": lambda: openclaw(a.root), "thclaws": lambda: thclaws(a.root)}
    sel = targets if a.runtime == "all" else {a.runtime: targets[a.runtime]}
    for n, f in sel.items(): f(); print("built", n)

if __name__ == "__main__":
    sys.exit(main())
