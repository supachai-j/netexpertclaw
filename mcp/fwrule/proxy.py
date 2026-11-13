#!/usr/bin/env python3
"""Lazy MCP stdio proxy (stdlib only) in front of a slow-starting server.

Why: some clients (Codex `exec`) build their tool list from the first seconds of a session and drop servers that answer
`initialize` late. This proxy answers `initialize` / `tools/list` / `ping` instantly from a cached, hash-checked tool list and
starts the real server only on the first other request (e.g. tools/call).

Safety properties (reviewed in docs/imports/fwrule-analyzer.md):
- tools/call requests and responses are forwarded byte-for-byte as JSON (params/result are not edited).
- Before the first forwarded request the real server's tools/list is compared with the cache (sha256); a mismatch makes every
  tools/call fail closed with a JSON-RPC error telling the operator to regenerate the cache (scripts/gen_tools_cache.py).
- The child gets a minimal environment (PATH, HOME, LANG, UV_*, XDG_CACHE_HOME, TMPDIR, SSL_CERT_*), nothing else.
- No network, no files other than the cache next to this script, no shell: child is started with an argv list.

Usage: proxy.py --cache tools.cache.json -- <child command...>
"""
import hashlib, json, os, subprocess, sys, threading

ALLOWED_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "XDG_CACHE_HOME", "XDG_DATA_HOME", "SSL_CERT_FILE", "SSL_CERT_DIR", "USER", "LOGNAME")


def canon(tools):  # canonical form of a tools/list result for hashing
    return json.dumps(sorted(tools, key=lambda t: t["name"]), sort_keys=True, separators=(",", ":"))


def tools_hash(tools): return hashlib.sha256(canon(tools).encode()).hexdigest()


def send(obj):
    sys.stdout.write(json.dumps(obj, separators=(",", ":")) + "\n"); sys.stdout.flush()


def err(i, code, msg): return {"jsonrpc": "2.0", "id": i, "error": {"code": code, "message": msg}}


class Child:
    def __init__(self, argv, init_params):
        env = {k: v for k, v in os.environ.items() if k in ALLOWED_ENV or k.startswith("UV_")}
        self.p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr, env=env, text=True, bufsize=1)
        self.lock = threading.Lock(); self.n = 0
        self.call("initialize", init_params)
        self.notify("notifications/initialized")

    def _write(self, o): self.p.stdin.write(json.dumps(o, separators=(",", ":")) + "\n"); self.p.stdin.flush()

    def notify(self, method, params=None):
        self._write({"jsonrpc": "2.0", "method": method, **({"params": params} if params is not None else {})})

    def call(self, method, params=None):
        with self.lock:
            self.n += 1; rid = f"p{self.n}"
            self._write({"jsonrpc": "2.0", "id": rid, "method": method, **({"params": params} if params is not None else {})})
            while True:
                line = self.p.stdout.readline()
                if not line: raise RuntimeError("child exited")
                try: m = json.loads(line)
                except ValueError: continue
                if m.get("id") == rid and ("result" in m or "error" in m): return m
                # child notifications / server requests are dropped (this server does not use them)


def main():
    a = sys.argv[1:]
    if "--" not in a or a[0] != "--cache": sys.exit("usage: proxy.py --cache FILE -- CMD...")
    cache_path, argv = a[1], a[a.index("--") + 1:]
    cache = json.load(open(cache_path))
    if tools_hash(cache["tools"]) != cache["sha256"]: sys.exit("tools cache corrupted (sha256 mismatch)")
    state = {"child": None, "ok": None, "init": None}

    def ensure():
        if state["child"] is None:
            c = Child(argv, state["init"]); r = c.call("tools/list")
            live = r.get("result", {}).get("tools", [])
            state["ok"] = (tools_hash(live) == cache["sha256"]); state["child"] = c
            if not state["ok"]: sys.stderr.write("netpaw proxy: live tools/list differs from cache; refusing tools/call\n")
        return state["child"]

    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try: m = json.loads(line)
        except ValueError: send(err(None, -32700, "parse error")); continue
        i, method, params = m.get("id"), m.get("method"), m.get("params")
        if method == "initialize":
            state["init"] = params
            send({"jsonrpc": "2.0", "id": i, "result": {"protocolVersion": (params or {}).get("protocolVersion", "2025-03-26"),
                  "capabilities": {"tools": {"listChanged": False}}, "serverInfo": cache["serverInfo"]}})
        elif method == "ping": send({"jsonrpc": "2.0", "id": i, "result": {}})
        elif method == "tools/list": send({"jsonrpc": "2.0", "id": i, "result": {"tools": cache["tools"]}})
        elif method and method.startswith("notifications/"): pass
        elif i is None: pass
        else:
            try:
                c = ensure()
                if not state["ok"]: send(err(i, -32001, "tool list changed upstream; regenerate tools cache and re-review")); continue
                r = c.call(method, params)
                r["id"] = i; send(r)
            except Exception as e:  # child failed to start / died
                send(err(i, -32002, f"proxy: {type(e).__name__}: {e}"))
    if state["child"]: state["child"].p.terminate()

if __name__ == "__main__":
    main()
