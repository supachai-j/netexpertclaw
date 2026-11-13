"""Spawn the MCP server exactly as .mcp.json would and call a tool over stdio."""
import asyncio, json, pathlib, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
R = pathlib.Path(__file__).resolve().parent.parent
async def main():
    e = json.loads((R/".mcp.json").read_text())["mcpServers"]["subnet-calc"]
    args = [a.replace("${CLAUDE_PLUGIN_ROOT}", str(R)) for a in e["args"]]
    async with stdio_client(StdioServerParameters(command=e["command"], args=args)) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = sorted(t.name for t in (await s.list_tools()).tools)
            res = await s.call_tool("subnet_calculator", {"cidr": "192.0.2.0/26"})
            txt = res.content[0].text
            assert "255.255.255.192" in txt and "62" in txt, txt
            bad = await s.call_tool("subnet_calculator", {"cidr": "192.0.2.5/26"})
            assert bad.isError, "host-bits input must error"
            print("tools:", tools); print("ok")
asyncio.run(main())
