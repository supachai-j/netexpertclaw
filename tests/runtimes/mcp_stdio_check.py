#!/usr/bin/env python3
"""Runtime-neutral MCP check for generated adapter configs (stdlib only).

Reads a generated MCP config (JSON `mcpServers` or Codex TOML `mcp_servers`),
spawns each server exactly as the config says, then does the MCP stdio
handshake: initialize -> tools/list -> tools/call. Prints one JSON line per
server with timings, so a slow first spawn (uv fetching deps) is visible.

usage: mcp_stdio_check.py <config.json|config.toml.snippet> [--timeout 120]
exit 0 = every server answered initialize + tools/list + a same_subnet call.
"""
import json, os, subprocess, sys, time

def load(path):
    txt = open(path, encoding="utf-8").read()
    if path.endswith(".json") or txt.lstrip().startswith("{"):
        return json.loads(txt)["mcpServers"]
    import tomllib
    return tomllib.loads(txt)["mcp_servers"]

def rpc(p, msg, want_id, deadline):
    p.stdin.write(json.dumps(msg) + "\n"); p.stdin.flush()
    while time.time() < deadline:
        line = p.stdout.readline()
        if not line:
            raise RuntimeError("server closed stdout")
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("id") == want_id:
            return r
    raise TimeoutError("no reply to id %s" % want_id)

def check(name, spec, timeout):
    env = dict(os.environ); env.update(spec.get("env") or {})
    t0 = time.time(); deadline = t0 + timeout
    p = subprocess.Popen([spec["command"], *spec.get("args", [])], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    out = {"server": name, "ok": False}
    try:
        r = rpc(p, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "nec-conformance", "version": "0"}}}, 1, deadline)
        out["t_initialize_s"] = round(time.time() - t0, 2)
        out["server_info"] = r["result"].get("serverInfo")
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"); p.stdin.flush()
        r = rpc(p, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, 2, deadline)
        out["tools"] = sorted(t["name"] for t in r["result"]["tools"])
        r = rpc(p, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
            "name": "same_subnet", "arguments": {"ip_a": "192.0.2.10", "ip_b": "192.0.2.20", "prefix": 24}}}, 3, deadline)
        out["same_subnet_reply"] = json.dumps(r.get("result", r.get("error")))[:200]
        out["ok"] = "same_subnet" in out["tools"] and not r.get("result", {}).get("isError")
        out["t_total_s"] = round(time.time() - t0, 2)
    except Exception as e:  # noqa: BLE001 - report, don't hide
        out["error"] = "%s: %s" % (type(e).__name__, e)
        try:
            p.kill(); out["stderr_tail"] = p.stderr.read()[-400:]
        except Exception:
            pass
    finally:
        try: p.kill()
        except Exception: pass
    return out

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    timeout = int(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 120
    if "--timeout" in sys.argv: args.remove(sys.argv[sys.argv.index("--timeout") + 1])
    res = [check(n, s, timeout) for n, s in load(args[0]).items()]
    for r in res: print(json.dumps(r, ensure_ascii=False))
    sys.exit(0 if all(r["ok"] for r in res) else 1)
