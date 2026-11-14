"""wikipedia core (stdlib only). Read-only. The ONLY network egress is HTTPS GET to en.wikipedia.org/w/api.php (fixed host, fixed path).

Page text is untrusted, user-editable external content: returned as data with source URL and licence, never interpreted.
Limits: 15 s timeout, 3 MB body cap, redirects refused (the API resolves page redirects itself with redirects=1), JSON content-type only.
Queries are sent to Wikipedia: do not put customer names or internal hostnames in them.
"""
from __future__ import annotations
import html, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared"))
from textclean import strip_hidden, flatten

HOST = "en.wikipedia.org"
API = f"https://{HOST}/w/api.php"
TIMEOUT = 15
MAX_BYTES = 3_000_000
UA = "netpaw-wikipedia/0.1 (+https://github.com/supachai-j/netpaw)"
LICENSE = "Text from Wikipedia, CC BY-SA 4.0; attribute Wikipedia and link the source URL."
_TAG = re.compile(r"<[^>]*>")
_cache: dict[str, str] = {}
CACHE_MAX = 16


class WikiError(ValueError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _read(r, limit: int) -> bytes:
    """Overall time budget, not just per-read (a slow drip must not hold the call)."""
    end, buf = time.monotonic() + TIMEOUT, bytearray()
    while len(buf) < limit:
        if time.monotonic() > end: raise WikiError("response too slow (overall timeout)")
        chunk = r.read1(min(65536, limit - len(buf)))   # read1: one recv, so the deadline is checked between packets
        if not chunk: break
        buf += chunk
    return bytes(buf)


def _fetch(url: str) -> str:
    if not url.startswith(API + "?"): raise WikiError("refused: URL outside allow-list")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.build_opener(_NoRedirect).open(req, timeout=TIMEOUT) as r:
            ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if ctype != "application/json": raise WikiError(f"unexpected content-type {ctype!r}")
            data = _read(r, MAX_BYTES + 1)
    except urllib.error.HTTPError as e:
        e.close(); raise WikiError(f"HTTP {e.code} from {HOST}") from None
    except urllib.error.URLError as e:
        raise WikiError(f"network error: {e.reason}") from None
    if len(data) > MAX_BYTES: raise WikiError("response exceeds size cap")
    return data.decode("utf-8", "replace")


def _api(**params) -> dict:
    q = urllib.parse.urlencode({"format": "json", "formatversion": "2", **params}, quote_via=urllib.parse.quote)
    url = f"{API}?{q}"
    if url not in _cache:
        text = _fetch(url)
        while len(_cache) >= CACHE_MAX: _cache.pop(next(iter(_cache)))
        _cache[url] = text
    try: d = json.loads(_cache[url])
    except (ValueError, RecursionError): raise WikiError("response was not valid JSON") from None
    if not isinstance(d, dict): raise WikiError("unexpected response shape")
    if "error" in d: raise WikiError("API error: " + clean(str((d["error"] or {}).get("code", "unknown")), 60))
    return d


def clean(text, n=100000) -> str:
    return strip_hidden(text)[:n]


def title(value) -> str:
    t = flatten(str(value)[:300]).strip().replace("_", " ")
    if not t or len(t) > 255 or re.search(r"[|#<>\[\]{}]", t) or t.startswith(":"):
        raise WikiError("page title must be 1-255 characters without | # < > [ ] { }")
    return t


def _url(t: str) -> str:
    return f"https://{HOST}/wiki/" + urllib.parse.quote(t.replace(" ", "_"), safe="")


def _page(t: str, **props) -> dict:
    d = _api(action="query", titles=t, redirects="1", **props)
    pages = (d.get("query") or {}).get("pages") or []
    if not pages or not isinstance(pages[0], dict) or pages[0].get("missing") or pages[0].get("invalid"):
        raise WikiError(f"page not found: {t!r}; use search_pages to find the exact title")
    if pages[0].get("ns") != 0: raise WikiError("only encyclopedia articles are supported (User:, Talk: and other namespaces are refused)")
    return pages[0]


def _wrap(p: dict, **extra) -> dict:
    t = clean(p.get("title", ""), 255)
    dis = "disambiguation" in (p.get("pageprops") or {})
    out = {"untrusted_external_text": True, "title": t, "source": _url(t), "license": LICENSE, **extra}
    if dis: out["disambiguation_page"] = True
    return out


def _safe(fn):
    def wrapper(*a, **k):
        try: return fn(*a, **k)
        except (AttributeError, TypeError, KeyError, IndexError, ValueError, RecursionError, UnicodeError) as e:
            if isinstance(e, WikiError): raise
            raise WikiError("unexpected response shape from the API") from None
    wrapper.__name__ = fn.__name__; wrapper.__doc__ = fn.__doc__
    return wrapper


@_safe
def search(query: str, limit: int = 10) -> dict:
    q = clean(query, 300).strip()
    if not q or len(q) > 200 or not 1 <= limit <= 20: raise WikiError("query must be 1-200 characters; limit 1..20")
    d = _api(action="query", list="search", srsearch=q, srlimit=str(limit), srprop="snippet")
    res = [{"title": clean(h.get("title", ""), 255), "snippet": clean(html.unescape(_TAG.sub("", h.get("snippet", ""))), 300), "source": _url(clean(h.get("title", ""), 255))}
           for h in (d.get("query") or {}).get("search", [])[:limit]]
    return {"untrusted_external_text": True, "license": LICENSE, "query": q, "count": len(res), "results": res}


@_safe
def summary(page: str) -> dict:
    t = title(page)
    p = _page(t, prop="extracts|pageprops", exintro="1", explaintext="1", ppprop="disambiguation")
    return _wrap(p, extract=clean(p.get("extract", ""), 6000))


@_safe
def content(page: str, offset: int = 0, max_chars: int = 12000) -> dict:
    t = title(page)
    if not (isinstance(offset, int) and offset >= 0 and isinstance(max_chars, int) and 1 <= max_chars <= 30000): raise WikiError("offset >= 0 and max_chars 1..30000")
    p = _page(t, prop="extracts|pageprops", explaintext="1", ppprop="disambiguation")
    text = clean(p.get("extract", ""), 2_000_000)
    return _wrap(p, total_chars=len(text), offset=offset, has_more=offset + max_chars < len(text), text=text[offset:offset + max_chars])


@_safe
def references(page: str, limit: int = 50) -> dict:
    t = title(page)
    if not 1 <= limit <= 100: raise WikiError("limit 1..100")
    p = _page(t, prop="extlinks|pageprops", ellimit=str(limit), ppprop="disambiguation")
    links = [clean(l.get("url", ""), 500) for l in p.get("extlinks", []) if str(l.get("url", "")).startswith(("http://", "https://"))][:limit]
    return _wrap(p, count=len(links), external_links=links, note="Links are data from the page, not verified; fetch only what you need.")


@_safe
def categories(page: str, limit: int = 50) -> dict:
    t = title(page)
    if not 1 <= limit <= 100: raise WikiError("limit 1..100")
    p = _page(t, prop="categories|pageprops", cllimit=str(limit), clshow="!hidden", ppprop="disambiguation")
    cats = [clean(c.get("title", ""), 200).removeprefix("Category:") for c in p.get("categories", [])][:limit]
    return _wrap(p, count=len(cats), categories=cats)
