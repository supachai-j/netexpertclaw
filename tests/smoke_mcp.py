"""Spawn the MCP server exactly as .mcp.json would and call a tool over stdio."""
import asyncio, json, pathlib, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
R = pathlib.Path(__file__).resolve().parent.parent
async def other(name, tool, expect):
    e = json.loads((R/".mcp.json").read_text())["mcpServers"][name]
    args = [a.replace("${CLAUDE_PLUGIN_ROOT}", str(R)) for a in e["args"]]
    async with stdio_client(StdioServerParameters(command=e["command"], args=args)) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            names = {t.name for t in (await s.list_tools()).tools}
            assert expect <= names, names
            ro = {x.name: bool(x.annotations and x.annotations.readOnlyHint) for x in (await s.list_tools()).tools}
            assert all(ro.values()), f"read server tools missing readOnlyHint: {ro}"
            res = await s.call_tool(tool, {})
            assert not res.isError and "panos" in res.content[0].text
            print(name, "ok", sorted(names))

async def rfc():
    e = json.loads((R/".mcp.json").read_text())["mcpServers"]["rfc-lookup"]
    assert "egress" not in e and "capability" not in e, "registry-only keys must not reach runtime configs"
    args = [a.replace("${CLAUDE_PLUGIN_ROOT}", str(R)) for a in e["args"]]
    async with stdio_client(StdioServerParameters(command=e["command"], args=args)) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tl = (await s.list_tools()).tools
            assert {t.name for t in tl} == {"get_rfc", "get_rfc_section", "search_rfcs"}, tl
            assert all(t.annotations and t.annotations.readOnlyHint and t.annotations.openWorldHint for t in tl)
            bad = await s.call_tool("get_rfc", {"number": "4271/../x"})   # rejected before any network access
            assert bad.isError and "RFC number" in bad.content[0].text, bad
            print("rfc-lookup ok", sorted(t.name for t in tl))

async def eve():
    e = json.loads((R/".mcp.json").read_text())["mcpServers"]["eve-lab"]
    args = [a.replace("${CLAUDE_PLUGIN_ROOT}", str(R)) for a in e["args"]]
    async with stdio_client(StdioServerParameters(command=e["command"], args=args)) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tl = (await s.list_tools()).tools
            assert [t.name for t in tl] == ["validate_unl_topology"] and tl[0].annotations.readOnlyHint and not tl[0].annotations.openWorldHint
            lab = '<lab name="t"><node id="1" name="R1"><interface id="0" network_id="1"/></node><node id="2" name="R2"><interface id="0" network_id="1"/></node><network id="1"/></lab>'
            ok = await s.call_tool("validate_unl_topology", {"unl_text": lab})
            assert not ok.isError and '"nodes": 2' in ok.content[0].text, ok
            bad = await s.call_tool("validate_unl_topology", {"unl_text": "<!DOCTYPE x><lab/>"})
            assert bad.isError and "DOCTYPE" in bad.content[0].text, bad
            print("eve-lab ok")

async def main():
    await eve()
    await rfc()
    await other("fwrule", "list_supported_vendors", {"parse_policy", "analyze_firewall_rule_overlap", "list_supported_vendors", "batch_analyze_overlap"})
    e = json.loads((R/".mcp.json").read_text())["mcpServers"]["subnet-calc"]
    args = [a.replace("${CLAUDE_PLUGIN_ROOT}", str(R)) for a in e["args"]]
    async with stdio_client(StdioServerParameters(command=e["command"], args=args)) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = sorted(t.name for t in (await s.list_tools()).tools)
            assert all(x.annotations and x.annotations.readOnlyHint for x in (await s.list_tools()).tools), "missing readOnlyHint"
            res = await s.call_tool("subnet_calculator", {"cidr": "192.0.2.0/26"})
            txt = res.content[0].text
            assert "255.255.255.192" in txt and "62" in txt, txt
            bad = await s.call_tool("subnet_calculator", {"cidr": "192.0.2.5/26"})
            assert bad.isError, "host-bits input must error"
            print("tools:", tools); print("ok")
asyncio.run(main())
