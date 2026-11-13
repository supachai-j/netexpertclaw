#!/usr/bin/env python3
"""Trigger eval for skill descriptions (agentskills.io 'Optimizing skill descriptions'), Claude Code adapter.

For every query in skills/<name>/evals/trigger_queries.json run `claude -p` N times with this checkout loaded as a plugin and record whether
the skill was used: a `Skill` tool call naming it, or a call to one of its MCP tools. A should-trigger query passes if trigger_rate > 0.5,
a should-not-trigger query passes if trigger_rate <= 0.5. Prints per-split pass rates (train guides edits, validation checks generalisation).

Safety: runs in an empty temp dir with an allow-list of tools (Skill + this plugin's MCP tools); Bash/Edit/Write/Web tools are disallowed,
so prompts cannot make the agent touch files or the network (rfc-lookup's own egress aside). Costs model quota: queries x runs invocations.
Usage: eval_triggers.py [--runs 1] [--jobs 4] [--split all|train|validation] [--out results.json] skill [skill...]
"""
import argparse, concurrent.futures as cf, json, os, pathlib, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from common import skills as load_skills

DENY = "Bash Edit Write NotebookEdit WebFetch WebSearch Task"


def triggered(events, skill, servers):
    for ev in events:
        if ev.get("type") != "assistant": continue
        for c in ev["message"]["content"]:
            if c.get("type") != "tool_use": continue
            n, inp = c.get("name", ""), c.get("input", {})
            if n == "Skill" and str(inp.get("skill", inp.get("name", ""))).split(":")[-1] == skill: return True
            if any(f"_{s}__" in n for s in servers): return True
    return False


def run_one(query, skill, servers, timeout):
    allowed = "Skill ToolSearch " + " ".join(f"mcp__plugin_netexpertclaw_{s}" for s in servers)
    with tempfile.TemporaryDirectory() as t:
        try:
            p = subprocess.run(["claude", "-p", query, "--plugin-dir", str(ROOT), "--output-format", "stream-json", "--verbose", "--max-turns", "4",
                                "--permission-mode", "default", "--allowedTools", allowed, "--disallowedTools", DENY],
                               cwd=t, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None
    ev = []
    for l in p.stdout.splitlines():
        try: ev.append(json.loads(l))
        except ValueError: pass
    if not any(e.get("type") == "result" for e in ev): return None
    return triggered(ev, skill, servers)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("skills", nargs="+"); ap.add_argument("--runs", type=int, default=1); ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--split", default="all"); ap.add_argument("--timeout", type=int, default=150); ap.add_argument("--out")
    a = ap.parse_args()
    meta = {s["dir"].name: s for s in load_skills()}
    jobs, report = [], {}
    for sk in a.skills:
        srv = [x.strip() for x in (meta[sk]["meta"]["metadata"].get("mcp_servers") or "").split(",") if x.strip()]
        qs = [q for q in json.loads((ROOT / "skills" / sk / "evals" / "trigger_queries.json").read_text()) if a.split in ("all", q["split"])]
        report[sk] = {"queries": [dict(q, runs=[]) for q in qs], "servers": srv}
        for q in report[sk]["queries"]:
            for _ in range(a.runs): jobs.append((sk, srv, q))
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        futs = {ex.submit(run_one, q["query"], sk, srv, a.timeout): q for sk, srv, q in jobs}
        for f in cf.as_completed(futs): futs[f]["runs"].append(f.result())
    for sk, r in report.items():
        for sp in ("train", "validation"):
            rows = [q for q in r["queries"] if q["split"] == sp]
            for q in rows:
                ok = [x for x in q["runs"] if x is not None]
                q["trigger_rate"] = sum(ok) / len(ok) if ok else None
                q["pass"] = None if q["trigger_rate"] is None else ((q["trigger_rate"] > 0.5) == q["should_trigger"])
            done = [q for q in rows if q["pass"] is not None]
            r[f"{sp}_pass"] = f"{sum(q['pass'] for q in done)}/{len(rows)}" + (f" ({len(rows) - len(done)} errored)" if len(done) != len(rows) else "")
        print(f"{sk}: train {r['train_pass']}  validation {r['validation_pass']}")
        for q in r["queries"]:
            if q["pass"] is False: print(f"   FAIL [{q['split']}] should_trigger={q['should_trigger']} rate={q['trigger_rate']}: {q['query'][:90]}")
    if a.out: pathlib.Path(a.out).write_text(json.dumps(report, indent=1, ensure_ascii=False))

if __name__ == "__main__":
    main()
