#!/usr/bin/env python3
"""Output eval (agentskills.io 'Evaluating skills'): does the skill make answers better than the same model without it?

For every eval in skills/<name>/evals/evals.json that has a `checks` list, run `claude -p` N times in two conditions:
  with_skill  - this checkout loaded as a plugin (Skill + the skill's MCP tools allowed)
  baseline    - no plugin, no tools
and grade the final answer with DETERMINISTIC checks (no LLM grader, so no second model call and no grader bias):
  {"type":"regex","pattern":P,"label":L}       answer must match P (numbers are normalised: 1,024 -> 1024)
  {"type":"not_regex","pattern":P,"label":L}   answer must not match P
  {"type":"vlsm","parent":CIDR,"need":[hosts,..]}  the answer lists CIDRs inside parent, non-overlapping, one big enough for each need
A run is INVALID (not counted, reported) if the with_skill run did not connect the skill's MCP server (e.g. `uv` not on PATH) or
never called one of its tools - otherwise a broken environment would look like "skill does not help".
Safety: empty temp cwd, tool allow-list, Bash/Edit/Write/Web denied. Costs model quota: evals x runs x 2 invocations.
Usage: eval_outputs.py [--runs 2] [--jobs 3] [--out results.json] skill [skill...]
"""
import argparse, concurrent.futures as cf, ipaddress, json, os, pathlib, re, shutil, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from common import skills as load_skills

DENY = "Bash Edit Write NotebookEdit WebFetch WebSearch Task"


def norm(t):
    return re.sub(r"(?<=\d),(?=\d{3}\b)", "", t)


def check_vlsm(text, c):
    parent = ipaddress.ip_network(c["parent"])
    nets = []
    for m in set(re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}\b", text)):
        try: n = ipaddress.ip_network(m)
        except ValueError: continue
        if n.version == parent.version and n != parent and n.subnet_of(parent): nets.append(n)  # type: ignore[arg-type]
    needs = sorted(c["need"], reverse=True)

    def pick(i, chosen):   # one listed subnet per requirement, inside parent, big enough, none overlapping (extra listed CIDRs, e.g. "unused space", are ignored)
        if i == len(needs): return True
        return any(n.num_addresses - 2 >= needs[i] and not any(n.overlaps(x) for x in chosen) and pick(i + 1, chosen + [n]) for n in sorted(nets, key=lambda n: n.num_addresses))
    if pick(0, []): return True, f"valid assignment among {len(nets)} listed subnets"
    return False, "no non-overlapping set of listed subnets inside the parent satisfies every requirement"


def grade(text, checks):
    t, res = norm(text), []
    for c in checks:
        k = c["type"]
        if k == "regex": ok, why = bool(re.search(c["pattern"], t, re.I)), c.get("label", c["pattern"])
        elif k == "not_regex": ok, why = not re.search(c["pattern"], t, re.I), c.get("label", c["pattern"])
        elif k == "vlsm": ok, why = check_vlsm(t, c)
        else: raise ValueError(k)
        res.append((ok, why))
    return res


def run_one(prompt, cond, servers, timeout, env):
    with tempfile.TemporaryDirectory() as d:
        cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose", "--max-turns", "6", "--disallowedTools", DENY]
        if cond == "with_skill":
            cmd += ["--plugin-dir", str(ROOT), "--allowedTools", "Skill ToolSearch " + " ".join(f"mcp__plugin_netexpertclaw_{s}" for s in servers)]
        try: p = subprocess.run(cmd, cwd=d, capture_output=True, text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired: return {"invalid": "timeout"}
    ev = []
    for l in p.stdout.splitlines():
        try: ev.append(json.loads(l))
        except ValueError: pass
    res = next((e for e in ev if e.get("type") == "result"), None)
    if not res: return {"invalid": "no result event"}
    used = [c["name"] for e in ev if e.get("type") == "assistant" for c in e["message"]["content"] if c.get("type") == "tool_use"]
    out = {"text": res.get("result", ""), "tools": used}
    if cond == "with_skill":
        init = next((e for e in ev if e.get("type") == "system" and e.get("subtype") == "init"), {})
        st = {s["name"]: s.get("status") for s in init.get("mcp_servers", [])}
        bad = [n for n, s in st.items() if any(sv in n for sv in servers) and s != "connected"]
        if bad: out["invalid"] = f"MCP not connected: {bad} (is uv on PATH?)"
        elif not any(any(f"_{sv}__" in u for sv in servers) for u in used): out["no_tool"] = True
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("skills", nargs="+"); ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--jobs", type=int, default=3); ap.add_argument("--timeout", type=int, default=240); ap.add_argument("--out"); ap.add_argument("--ids")
    a = ap.parse_args()
    env = dict(os.environ)
    if not shutil.which("uv"):
        for d in (pathlib.Path.home() / ".hermes" / "bin", pathlib.Path.home() / ".local" / "bin"):
            if (d / "uv").exists(): env["PATH"] = f"{d}:{env['PATH']}"; break
    meta = {s["dir"].name: s for s in load_skills()}
    jobs, report = [], {}
    for sk in a.skills:
        srv = [x.strip() for x in (meta[sk]["meta"]["metadata"].get("mcp_servers") or "").split(",") if x.strip()]
        evs = [e for e in json.loads((ROOT / "skills" / sk / "evals" / "evals.json").read_text())["evals"] if e.get("checks") and (not a.ids or str(e["id"]) in a.ids.split(","))]
        report[sk] = {e["id"]: {"prompt": e["prompt"], "checks": e["checks"], "with_skill": [], "baseline": []} for e in evs}
        for e in evs:
            for cond in ("with_skill", "baseline"):
                for _ in range(a.runs): jobs.append((sk, e, cond, srv))
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        futs = {ex.submit(run_one, e["prompt"], cond, srv, a.timeout, env): (sk, e, cond) for sk, e, cond, srv in jobs}
        for f in cf.as_completed(futs):
            sk, e, cond = futs[f]; r = f.result()
            if "text" in r:
                g = grade(r["text"], e["checks"]); r["grade"] = g; r["pass"] = all(ok for ok, _ in g)  # type: ignore[assignment]
            report[sk][e["id"]][cond].append(r)
    for sk, evs in report.items():
        print(f"== {sk}")
        for i, e in evs.items():
            row = []
            for cond in ("with_skill", "baseline"):
                rs = [r for r in e[cond] if "invalid" not in r]; inv = len(e[cond]) - len(rs)
                row.append(f"{cond} {sum(r['pass'] for r in rs)}/{len(rs)}" + (f" ({inv} invalid)" if inv else "") + (f" [no tool call in {sum(1 for r in rs if r.get('no_tool'))}]" if cond == "with_skill" and any(r.get("no_tool") for r in rs) else ""))
            print(f"  eval {i}: " + "  |  ".join(row) + f"   {e['prompt'][:60]}")
            for cond in ("with_skill", "baseline"):
                for r in e[cond]:
                    if "invalid" in r: print(f"     {cond} INVALID: {r['invalid']}")
                    elif not r["pass"]: print(f"     {cond} failed: " + "; ".join(w for ok, w in r["grade"] if not ok)[:140])
    if a.out: pathlib.Path(a.out).write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
