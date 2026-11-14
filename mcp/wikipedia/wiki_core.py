"""wikipedia core (stdlib only). Read-only. The ONLY network egress is HTTPS GET to en.wikipedia.org/w/api.php (fixed host, fixed path).

Page text is untrusted, user-editable external content: returned as data with source URL and licence, never interpreted.
Limits: 15 s timeout, 3 MB body cap, redirects refused (the API resolves page redirects itself with redirects=1), JSON content-type only.
Queries are sent to Wikipedia: do not put customer names or internal hostnames in them.
"""
from __future__ import annotations
import html, json, re, urllib.error, urllib.parse, urllib.request

HOST = "en.wikipedia.org"
API = f"https://{HOST}/w/api.php"
TIMEOUT = 15
MAX_BYTES = 3_000_000
UA = "netexpertclaw-wikipedia/0.1 (+https://github.com/supachai-j/netexpertclaw)"
LICENSE = "Text from Wikipedia, CC BY-SA 4.0; attribute Wikipedia and link the source URL."
_BAD = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f\u00ad\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]")
_TAG = re.compile(r"<[^>]*>")
_cache: dict[str, str] = {}
CACHE_MAX = 16


class WikiError(ValueError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _fetch(url: str) -> str:
    if not url.startswith(API + "?"): raise WikiError("refused: URL outside allow-list")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.build_opener(_NoRedirect).open(req, timeout=TIMEOUT) as r:
            ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if ctype != "application/json": raise WikiError(f"unexpected content-type {ctype!r}")
            data = r.read(MAX_BYTES + 1)
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
    except ValueError: raise WikiError("response was not valid JSON") from None
    if not isinstance(d, dict): raise WikiError("unexpected response shape")
    if "error" in d: raise WikiError("API error: " + clean(str((d["error"] or {}).get("code", "unknown")), 60))
    return d


def clean(text, n=100000) -> str:
    return _BAD.sub("", str(text))[:n]


def title(value) -> str:
    t = clean(value, 300).strip().replace("_", " ")
    if not t or len(t) > 255 or re.search(r"[|#<>\[\]{}]", t) or t.startswith(":"):
        raise WikiError("page title must be 1-255 characters without | # < > [ ] { }")
    return t


def _url(t: str) -> str:
    return f"https://{HOST}/wiki/" + urllib.parse.quote(t.replace(" ", "_"), safe="")


def _page(t: str, **props) -> dict:
    d = _api(action="query", titles=t, redirects="1", **props)
    pages = (d.get("query") or {}).get("pages") or []
    if not pages or pages[0].get("missing") or pages[0].get("invalid"):
        raise WikiError(f"page not found: {t!r}; use search_pages to find the exact title")
    return pages[0]


def _wrap(p: dict, **extra) -> dict:
    t = clean(p.get("title", ""), 255)
    dis = "disambiguation" in (p.get("pageprops") or {})
    out = {"untrusted_external_text": True, "title": t, "source": _url(t), "license": LICENSE, **extra}
    if dis: out["disambiguation_page"] = True
    return out


def search(query: str, limit: int = 10) -> dict:
    q = clean(query, 300).strip()
    if not q or len(q) > 200 or not 1 <= limit <= 20: raise WikiError("query must be 1-200 characters; limit 1..20")
    d = _api(action="query", list="search", srsearch=q, srlimit=str(limit), srprop="snippet")
    res = [{"title": clean(h.get("title", ""), 255), "snippet": clean(html.unescape(_TAG.sub("", h.get("snippet", ""))), 300), "source": _url(clean(h.get("title", ""), 255))}
           for h in (d.get("query") or {}).get("search", [])[:limit]]
    return {"untrusted_external_text": True, "license": LICENSE, "query": q, "count": len(res), "results": res}


def summary(page: str) -> dict:
    t = title(page)
    p = _page(t, prop="extracts|pageprops", exintro="1", explaintext="1", ppprop="disambiguation")
    return _wrap(p, extract=clean(p.get("extract", ""), 6000))


def content(page: str, offset: int = 0, max_chars: int = 12000) -> dict:
    t = title(page)
    if not (isinstance(offset, int) and offset >= 0 and isinstance(max_chars, int) and 1 <= max_chars <= 30000): raise WikiError("offset >= 0 and max_chars 1..30000")
    p = _page(t, prop="extracts|pageprops", explaintext="1", ppprop="disambiguation")
    text = clean(p.get("extract", ""), 2_000_000)
    return _wrap(p, total_chars=len(text), offset=offset, has_more=offset + max_chars < len(text), text=text[offset:offset + max_chars])


def references(page: str, limit: int = 50) -> dict:
    t = title(page)
    if not 1 <= limit <= 100: raise WikiError("limit 1..100")
    p = _page(t, prop="extlinks|pageprops", ellimit=str(limit), ppprop="disambiguation")
    links = [clean(l.get("url", ""), 500) for l in p.get("extlinks", []) if str(l.get("url", "")).startswith(("http://", "https://"))][:limit]
    return _wrap(p, count=len(links), external_links=links, note="Links are data from the page, not verified; fetch only what you need.")


def categories(page: str, limit: int = 50) -> dict:
    t = title(page)
    if not 1 <= limit <= 100: raise WikiError("limit 1..100")
    p = _page(t, prop="categories|pageprops", cllimit=str(limit), clshow="!hidden", ppprop="disambiguation")
    cats = [clean(c.get("title", ""), 200).removeprefix("Category:") for c in p.get("categories", [])][:limit]
    return _wrap(p, count=len(cats), categories=cats)
