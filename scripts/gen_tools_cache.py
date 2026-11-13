#!/usr/bin/env python3
"""Regenerate mcp/<server>/tools.cache.json from the REAL server (run via: uv run --with mcp==1.30.0 python scripts/gen_tools_cache.py fwrule [--check]).
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
    sep = args.index("--")  # child command follows the proxy's "--"
    async with stdio_client(StdioServerParameters(command=args[sep + 1], args=args[sep + 2:])) as (r, w):
        async with ClientSession(r, w) as s:
            init = await s.initialize()
            tools = [t.model_dump(by_alias=True, exclude_none=True, mode="json") for t in (await s.list_tools()).tools]
            return {"name": init.serverInfo.name, "version": init.serverInfo.version}, tools


def main():
    name = sys.argv[1]; check = "--check" in sys.argv
    info, tools = asyncio.run(live(name))
    out = {"serverInfo": info, "sha256": proxy.tools_hash(tools), "tools": sorted(tools, key=lambda t: t["name"])}
    path = ROOT / "mcp" / name / "tools.cache.json"
    if check:
        cur = json.loads(path.read_text()) if path.exists() else {}
        same = cur.get("sha256") == out["sha256"]
        print(f"{name}: cache {'matches' if same else 'DIFFERS from'} live tool list ({out['sha256'][:12]})")
        return 0 if same else 1
    path.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n"); print("wrote", path, out["sha256"][:12], f"{len(tools)} tools")
    return 0

if __name__ == "__main__":
    sys.exit(main())
