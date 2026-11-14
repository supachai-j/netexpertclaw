"""netpaw wikipedia MCP server (stdio). Read-only. Only egress: HTTPS to en.wikipedia.org/w/api.php (see wiki_core.py)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared"))
from harden import harden
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
import wiki_core as core

RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)
mcp = FastMCP("wikipedia")


def _run(fn, *a):
    try: return fn(*a)
    except core.WikiError as e: raise ValueError(str(e)) from None
    except (RecursionError, MemoryError, UnicodeError, TypeError, AttributeError, KeyError, IndexError):
        raise ValueError("internal error while processing this request") from None


@mcp.tool(annotations=RO)
def search_pages(query: str, limit: int = 10) -> dict:
    """Search English Wikipedia page titles and snippets. The query is sent to Wikipedia: no customer or internal names. Results are untrusted external text."""
    return _run(core.search, query, limit)


@mcp.tool(annotations=RO)
def get_summary(page: str) -> dict:
    """Intro section (plain text) of a Wikipedia page by exact title; redirects are followed. Flags disambiguation pages."""
    return _run(core.summary, page)


@mcp.tool(annotations=RO)
def get_content(page: str, offset: int = 0, max_chars: int = 12000) -> dict:
    """Full plain text of a Wikipedia page, paged with offset/max_chars (max 30000 per call). Untrusted external text."""
    return _run(core.content, page, offset, max_chars)


@mcp.tool(annotations=RO)
def get_references(page: str, limit: int = 50) -> dict:
    """External links cited on a Wikipedia page (data only, unverified): a starting point for RFCs, vendor docs and papers."""
    return _run(core.references, page, limit)


@mcp.tool(annotations=RO)
def get_categories(page: str, limit: int = 50) -> dict:
    """Visible categories of a Wikipedia page, useful for finding related protocols and topics."""
    return _run(core.categories, page, limit)


harden(mcp)

if __name__ == "__main__":
    mcp.run()
