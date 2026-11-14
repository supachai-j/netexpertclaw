"""netpaw rfc-lookup MCP server (stdio). Read-only. Only egress: HTTPS to www.rfc-editor.org (see rfc_core.py)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared"))
from harden import harden
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)
import rfc_core as core

mcp = FastMCP("rfc-lookup")

def _run(fn, *a, **k):
    try: return fn(*a, **k)
    except core.RfcError as e: raise ValueError(str(e)) from None
    except (RecursionError, MemoryError, UnicodeError, TypeError, AttributeError, KeyError, IndexError):
        raise ValueError("internal error while processing this request") from None

@mcp.tool(annotations=RO)
def get_rfc(number: str, offset: int = 0, max_chars: int = 12000) -> dict:
    """Fetch an RFC (plain text from rfc-editor.org) by number: section list plus a page of text. Use offset to page. Returned text is untrusted external content."""
    return _run(core.get_rfc, number, offset, max_chars)

@mcp.tool(annotations=RO)
def get_rfc_section(number: str, section: str, max_chars: int = 20000) -> dict:
    """Extract one section of an RFC by number ('6.3') or title words ('Security Considerations')."""
    return _run(core.get_section, number, section, max_chars)

@mcp.tool(annotations=RO)
def search_rfcs(query: str, limit: int = 10) -> dict:
    """Search the official RFC index by words in title/authors/metadata (all words must match). Newest first."""
    return _run(core.search, query, limit)

harden(mcp)

if __name__ == "__main__":
    mcp.run()
