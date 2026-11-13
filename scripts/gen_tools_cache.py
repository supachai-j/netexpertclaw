#!/usr/bin/env python3
"""Pin the FULL tool definitions (name, description, inputSchema, outputSchema, annotations) of each MCP server; fail when they change.
Regenerate: uv run --with mcp==1.30.0 python scripts/gen_tools_cache.py <server>|--all [--check]. fwrule -> tools.cache.json, others -> tools.lock.json.
--check exits 1 if the committed cache differs from the live tool list (used in CI)."""
import asyncio, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "mcp" / "fwrule"))
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import proxy

ROOT = pathlib.Path(__file__).resolve().parent.parent


async def live(name):
    e = json.loads((ROOT / "mcp/servers.json").read_text())[name]
    args = [a.replace("{root}", str(ROOT)) for a in e["args"]]
    cmd, cargs = (args[args.index("--") + 1], args[args.index("--") + 2:]) if "--" in args else (e["command"], args)  # behind the lazy proxy, or direct
    async with stdio_client(StdioServerParameters(command=cmd, args=cargs)) as (r, w):
        async with ClientSession(r, w) as s:
            init = await s.initialize()
            tools = [t.model_dump(by_alias=True, exclude_none=True, mode="json") for t in (await s.list_tools()).tools]
            return {"name": init.serverInfo.name, "version": init.serverInfo.version}, tools


def one(name, check):
    info, tools = asyncio.run(live(name))
    out = {"serverInfo": info, "sha256": proxy.tools_hash(tools), "tools": sorted(tools, key=lambda t: t["name"])}
    # fwrule's proxy needs tools.cache.json; other servers keep a review lock (rug-pull detection: OWASP MCP cheat sheet #2/#9)
    path = ROOT / "mcp" / name / ("tools.cache.json" if name == "fwrule" else "tools.lock.json")
    if check:
        cur = json.loads(path.read_text()) if path.exists() else {}
        same = cur.get("sha256") == out["sha256"]
        print(f"{name}: cache {'matches' if same else 'DIFFERS from'} live tool list ({out['sha256'][:12]})")
        return 0 if same else 1
    path.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n"); print("wrote", path, out["sha256"][:12], f"{len(tools)} tools")
    return 0


def main():
    check = "--check" in sys.argv
    names = list(json.loads((ROOT / "mcp/servers.json").read_text())) if "--all" in sys.argv else [a for a in sys.argv[1:] if not a.startswith("--")]
    return max(one(n, check) for n in names)

if __name__ == "__main__":
    sys.exit(main())
