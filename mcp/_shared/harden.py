"""Shared MCP server hardening (OWASP MCP cheat sheet #2 and #5): strict input schemas, enforced server-side.

- advertises `additionalProperties: false` in every tool's inputSchema
- rejects unknown arguments at call time (pydantic extra=forbid) instead of silently ignoring them
Uses FastMCP internals (`_tool_manager`), so it is covered by tests/test_harden.py and must be re-checked when `mcp` is bumped.
"""


def harden(mcp) -> None:
    for tool in mcp._tool_manager._tools.values():
        tool.parameters["additionalProperties"] = False
        model = tool.fn_metadata.arg_model
        model.model_config["extra"] = "forbid"
        model.model_rebuild(force=True)
