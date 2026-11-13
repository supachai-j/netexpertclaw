"""Launcher for the pinned fwrule-mcp server: adds MCP safety annotations (readOnlyHint) that upstream omits.
Runtimes (Codex exec, OpenClaw) use them to decide approval. All four upstream tools were reviewed as analysis-only
(docs/imports/fwrule-analyzer.md). Fails closed: if a tool name is unknown/new, refuse to start rather than mark it read-only."""
import asyncio, sys
from mcp.types import ToolAnnotations
import fwrule_mcp.server as s

REVIEWED = {"analyze_firewall_rule_overlap", "batch_analyze_overlap", "list_supported_vendors", "parse_policy"}
RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

async def annotate():
    tools = await s.mcp.list_tools()
    names = {t.name for t in tools}
    if names != REVIEWED:
        sys.exit(f"fwrule launcher: tool set changed {sorted(names ^ REVIEWED)}; re-review before use")
    for n in names:
        (await s.mcp.get_tool(n)).annotations = RO

asyncio.run(annotate())
s.main()
