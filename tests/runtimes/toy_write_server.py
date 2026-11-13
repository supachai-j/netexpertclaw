"""TOY MCP server for approval-gate tests. No device, no network: the 'write' only creates a marker file.
Tools: read_state (readOnlyHint=true) and apply_change (destructiveHint=true, readOnlyHint=false).
Env TOY_MARKER = path of the marker file written by apply_change."""
import os, pathlib
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

mcp = FastMCP("toy-write")

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False))
def read_state() -> dict:
    """Read-only: report whether the marker exists."""
    return {"marker_exists": pathlib.Path(os.environ["TOY_MARKER"]).exists()}

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False))
def apply_change(text: str) -> dict:
    """WRITE (toy): create the marker file with the given text. Stands in for a device config change."""
    pathlib.Path(os.environ["TOY_MARKER"]).write_text(text)
    return {"applied": True}

if __name__ == "__main__":
    mcp.run()
