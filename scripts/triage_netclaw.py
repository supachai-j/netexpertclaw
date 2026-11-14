#!/usr/bin/env python3
"""Triage every NetClaw skill (pinned checkout) into an import class, from text signals only. Nothing is imported or executed.
Usage: triage_netclaw.py <netclaw-checkout> [--out docs/imports/NETCLAW-TRIAGE]
Classes (first match wins):
  blocked-write   its own body (boilerplate sections like "Integration with Other Skills" removed) names a write-style tool (create_/delete_/push_/apply_/send_...) or ITSM/chat/email
  needs-creds     needs credentials/env or a live platform (device inventory, controller, cloud, SaaS) but no write signal
  egress-public   read-only, public internet only (RFC, registries, advisories) - needs egress allow-list
  offline-doc     no credentials, no network signal, no MCP tool: pure workflow/reference skill
  offline-tool    needs a local MCP server/script but no creds/network
The signals are keyword heuristics and WILL misclassify some skills; every import still gets a human read of the source (docs/imports/<skill>.md).
"""
import json, pathlib, re, sys, collections
ROOT = pathlib.Path(sys.argv[1]).resolve(); SK = ROOT / "workspace" / "skills"
out = pathlib.Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else pathlib.Path("docs/imports/NETCLAW-TRIAGE")
WRITE = re.compile(r"\b(push(es|ed)? config|commit(s|ted)? (the )?(config|change)|write[- ]mem|configure terminal|conf t\b|delete[_ ]|create[_ ](network|node|lab|ticket|incident|issue|vlan|rule|policy|user)|apply[_ ]|deploy|rollback|reload|reboot|shutdown|send[_ ](message|email|mail)|post(s|ed)? (a )?(message|comment)|open(s|ed)? (a )?(ticket|incident|pr|pull request)|merge[_ ]|terraform apply|kubectl (apply|delete)|set_|update_(config|policy)|change request|servicenow|jira|slack|webex|teams|pagerduty|email)\b", re.I)
CRED = re.compile(r"(_(TOKEN|PASSWORD|API_KEY|SECRET|USER(NAME)?)\b|\bAPI[_ ]key\b|\bcredential|testbed\.ya?ml|\binventory\b|\bssh\b|\bnetconf\b|\brestconf\b|\bgnmi\b|\bsnmp\b|controller|\bBearer\b|\boauth|\btenant\b|\bAWS_|\bAZURE_|\bGCP\b)", re.I)
NET = re.compile(r"(https?://[^\s)\"'`>]+|npx -y|pip install|curl |wget |uvx |docker run)", re.I)
UNPIN = re.compile(r"npx -y [^\s@]+(\s|$)|curl[^\n|]*\|\s*(ba)?sh", re.I)
BOILER = re.compile(r"(?ms)^## (Integration with [^\n]*|Failure Behavior|GAIT Audit Trail|Example Queries|Error Handling|Related Skills)\s*\n.*?(?=^## |\Z)")
WTOOL = re.compile(r"`((?:create|delete|remove|set|push|apply|commit|configure|send|post|update|restart|reload|deploy|add|execute|exec|run|write|put|patch|enable|disable|clear|reset|assign|approve|merge|open|close|shutdown|rollback|upload|import|kill|block|unblock|isolate|quarantine)_[a-z0-9_]+)`")
ITSM = re.compile(r"\b(servicenow|jira|slack|webex|pagerduty|email)\b", re.I)
SAFE_ENV = re.compile(r"^(MCP_CALL|[A-Z0-9]+_MCP_SCRIPT|[A-Z0-9_]*_SCRIPT|[A-Z0-9_]*_MCP_(CMD|PATH))$")
rows = []
for d in sorted(p for p in SK.iterdir() if p.is_dir() and (p / "SKILL.md").exists()):
    t = (d / "SKILL.md").read_text(errors="replace"); allt = t + "".join(f.read_text(errors="replace") for f in d.rglob("*.md") if f.name != "SKILL.md")
    fm = re.match(r"---\n(.*?)\n---", t, re.S); fm = fm.group(1) if fm else ""
    desc = (re.search(r"(?m)^description:\s*(.*)$", fm) or [0, ""])[1].strip(" \"'")
    env = sorted(set(re.findall(r'"env":\s*\[([^\]]*)\]', fm) and re.findall(r"[A-Z][A-Z0-9_]{3,}", ",".join(re.findall(r'"env":\s*\[([^\]]*)\]', fm)))))
    hosts = sorted({re.sub(r"^https?://", "", u).split("/")[0].lower() for u in re.findall(r"https?://[^\s)\"'`>]+", allt)} - {"example.com", "localhost"})[:6]
    body = BOILER.sub("", t)
    wt = sorted(set(WTOOL.findall(body)))
    cenv = [e for e in env if not SAFE_ENV.match(e)]
    w = bool(wt) or bool(re.search(r"\b(push(es|ed)? config|write[- ]mem|configure terminal|terraform apply|kubectl (apply|delete))\b", body, re.I)) or bool(ITSM.search(body))
    c = bool(cenv) or bool(CRED.search(body))
    scripts = [f.name for f in d.rglob("*") if f.is_file() and f.suffix in (".py", ".sh", ".js", ".ts")]
    mcp = "mcp" in allt.lower() or "mcp_call" in allt.lower()
    net = bool(hosts) or bool(NET.search(allt))
    if w: cls = "blocked-write"
    elif c: cls = "needs-creds"
    elif net and (mcp or hosts): cls = "egress-public"
    elif mcp or scripts: cls = "offline-tool"
    else: cls = "offline-doc"
    rows.append({"skill": d.name, "class": cls, "lines": t.count("\n") + 1, "env": cenv, "write_tools": wt[:6], "hosts": hosts, "scripts": scripts, "mcp": mcp, "unpinned_runner": bool(UNPIN.search(allt)), "description": desc[:140]})
cnt = collections.Counter(r["class"] for r in rows)
out.with_suffix(".json").write_text(json.dumps({"netclaw_commit": __import__("subprocess").run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(), "counts": cnt, "skills": rows}, indent=1))
md = ["# NetClaw skill triage (heuristic, text signals only)\n", f"Source: NetClaw @ {json.loads(out.with_suffix('.json').read_text())['netclaw_commit'][:12]} (Apache-2.0). {len(rows)} skills. Generated by scripts/triage_netclaw.py; nothing was imported or executed.\n", "Counts: " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items())) + "\n"]
for k in ("offline-doc", "offline-tool", "egress-public", "needs-creds", "blocked-write"):
    md.append(f"\n## {k} ({cnt[k]})\n")
    for r in rows:
        if r["class"] == k: md.append(f"- `{r['skill']}` ({r['lines']} lines){' scripts=' + ','.join(r['scripts'][:3]) if r['scripts'] else ''}{' env=' + ','.join(r['env'][:3]) if r['env'] else ''}{' WRITE:' + ','.join(r['write_tools'][:3]) if r['write_tools'] else ''}{' UNPINNED' if r['unpinned_runner'] else ''}")
out.with_suffix(".md").write_text("\n".join(md) + "\n")
print(dict(cnt), len(rows))
