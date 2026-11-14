"""netpaw eve-lab MCP server (stdio). Read-only, offline: validates EVE-NG .unl topology TEXT. No network, no file or path arguments."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared"))
from harden import harden
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
import eve_core as core

RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
mcp = FastMCP("eve-lab")


@mcp.tool(annotations=RO)
def validate_unl_topology(unl_text: str, requirements_json: str = "", roles_json: str = "") -> dict:
    """Validate the text of an EVE-NG .unl lab: orphan nodes, dangling interfaces, partitions, forbidden role adjacency, single points of failure, link symmetry, and optional requirements (required_links, forbidden_links, redundancy_groups as JSON). Returns PASS/WARN/FAIL lists and a resilience level. Pass the file CONTENT, not a path. Node names in the result come from the file (untrusted)."""
    try: return core.validate(unl_text, requirements_json, roles_json)
    except core.UnlError as e: raise ValueError(str(e)) from None


harden(mcp)

if __name__ == "__main__":
    mcp.run()
