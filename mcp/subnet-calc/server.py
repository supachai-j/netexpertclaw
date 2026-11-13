"""netexpertclaw subnet-calc MCP server (stdio). Read-only; no network or device access."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared"))
from harden import harden
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
import core

mcp = FastMCP("subnet-calc")

@mcp.tool(annotations=RO)
def subnet_calculator(cidr: str) -> dict:
    """IPv4 CIDR details: mask, wildcard, usable hosts, neighbours, classification. cidr must be canonical (no host bits)."""
    return core.subnet_v4(cidr)

@mcp.tool(annotations=RO)
def subnet_calculator_v6(cidr: str) -> dict:
    """IPv6 CIDR details: range, /64 count, neighbours, classification, allocation note."""
    return core.subnet_v6(cidr)

@mcp.tool(annotations=RO)
def subnet_calculator_auto(cidr: str) -> dict:
    """Auto-detect IPv4/IPv6 and calculate."""
    return core.subnet_auto(cidr)

@mcp.tool(annotations=RO)
def same_subnet(ip_a: str, ip_b: str, prefix: int) -> dict:
    """Check whether two addresses fall in the same /prefix subnet."""
    return core.same_subnet(ip_a, ip_b, prefix)

harden(mcp)

if __name__ == "__main__":
    mcp.run()
