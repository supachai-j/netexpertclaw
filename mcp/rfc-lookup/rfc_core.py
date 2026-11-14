"""rfc-lookup core (stdlib only). Read-only. The ONLY network egress is HTTPS GET to www.rfc-editor.org (fixed allow-list).

Fetched text is untrusted external content: it is returned as data with its source URL, never executed or interpreted.
Limits: 15 s timeout, 5 MB (RFC) / 4 MB (index) body cap, redirects refused, content-type must be text/plain.
"""
from __future__ import annotations
import os, re, sys, time, urllib.error, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared"))
from textclean import strip_hidden

HOST = "www.rfc-editor.org"
TIMEOUT = 15
MAX_RFC_BYTES = 5_000_000
MAX_INDEX_BYTES = 4_000_000
UA = "netpaw-rfc-lookup/0.1 (+https://github.com/supachai-j/netpaw)"
_cache: dict[str, str] = {}   # in-memory only; nothing is written to disk
CACHE_MAX = 16                # entries (each up to 5 MB); oldest dropped first


def _cached(url: str, cap: int) -> str:
    if url not in _cache:
        text = _fetch(url, cap)
        while len(_cache) >= CACHE_MAX: _cache.pop(next(iter(_cache)))
        _cache[url] = text
    return _cache[url]


class RfcError(ValueError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None   # refuse every redirect: a fixed host must answer directly


def _read(r, limit: int) -> bytes:
    """Read at most `limit` bytes within an overall TIMEOUT-second budget (the socket timeout alone applies per read, so a slow drip could hold the call)."""
    end, buf = time.monotonic() + TIMEOUT, bytearray()
    while len(buf) < limit:
        if time.monotonic() > end: raise RfcError("response too slow (overall timeout)")
        chunk = r.read1(min(65536, limit - len(buf)))   # read1: one recv, so the deadline is checked between packets (read(n) would block until n bytes)
        if not chunk: break
        buf += chunk
    return bytes(buf)


def _fetch(url: str, cap: int) -> str:
    if not url.startswith(f"https://{HOST}/"):
        raise RfcError("refused: URL outside allow-list")
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/plain"})
    try:
        with opener.open(req, timeout=TIMEOUT) as r:
            ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if ctype != "text/plain":
                raise RfcError(f"unexpected content-type {ctype!r}")
            data = _read(r, cap + 1)
    except urllib.error.HTTPError as e:
        e.close()
        raise RfcError(f"HTTP {e.code} from {HOST}") from None
    except urllib.error.URLError as e:
        raise RfcError(f"network error: {e.reason}") from None
    if len(data) > cap:
        raise RfcError("response exceeds size cap")
    return data.decode("utf-8", "replace")


def parse_number(value) -> int:
    s = str(value).strip().lower().removeprefix("rfc").strip()
    if not re.fullmatch(r"[0-9]{1,5}", s) or int(s) < 1:
        raise RfcError("RFC number must be 1-5 digits (e.g. 4271 or 'RFC 4271')")
    return int(s)


def load_rfc(number) -> tuple[int, str, str]:
    n = parse_number(number)
    url = f"https://{HOST}/rfc/rfc{n}.txt"
    return n, url, _cached(url, MAX_RFC_BYTES)


_FOOT = re.compile(r".*\[Page \d+\]\s*$")
_HEAD = re.compile(r"^RFC \d{1,5} {2,40}[^ ].{0,100}? {2,40}\w{3,9} \d{4} *$")   # bounded: the unbounded form was cubic on hostile whitespace (review H2-3)


def strip_invisible(text: str) -> str:
    """Remove control and invisible/format characters (see mcp/_shared/textclean.py); tab and newline are kept."""
    return strip_hidden(text)


def clean(text: str) -> list[str]:
    """Drop page-break furniture (form feeds, page footers/headers); keep the text."""
    out = []
    for line in strip_invisible(text.replace("\r", "")).split("\n"):
        if len(line) <= 200 and (_FOOT.match(line) or _HEAD.match(line)):
            continue
        out.append(line.rstrip())
    return out


_HEADING = re.compile(r"^((?:[0-9]+\.)+[0-9]*|[0-9]+|Appendix [A-Z](?:\.[0-9]+)*\.?|[A-Z]\.[0-9.]*)\s{1,3}([A-Za-z].*)$")


_UNNUMBERED = re.compile(r"^(Abstract|Status of This Memo|Copyright Notice|IANA Considerations|Security Considerations|"
                         r"Privacy Considerations|References|Normative References|Informative References|Acknowledg(?:e)?ments|"
                         r"Contributors|Authors?'? Addresses|Author'?s? Address|Appendices)\s*$")


def depth(num: str) -> int:
    return num.replace("Appendix ", "").strip().rstrip(".").count(".")


def headings(lines: list[str]) -> list[tuple[int, str, str]]:
    """(line_index, number, title) for column-0 numbered headings, skipping the table of contents."""
    out, in_toc = [], False
    for i, l in enumerate(lines):
        if l.strip() == "Table of Contents":
            in_toc = True; continue
        if in_toc and re.match(r"^[0-9]+\.\s", l):
            in_toc = False
        if in_toc or l.startswith(" "):
            continue
        m = _HEADING.match(l)
        if m and not re.search(r"\.{3,}", l):
            out.append((i, m.group(1).rstrip("."), m.group(2).strip()))
        elif _UNNUMBERED.match(l):
            out.append((i, "", l.strip()))
    return out


def get_rfc(number, offset: int = 0, max_chars: int = 12000) -> dict:
    n, url, text = load_rfc(number)
    if not (0 <= offset) or not (1 <= max_chars <= 50000):
        raise RfcError("offset must be >= 0 and max_chars 1..50000")
    body = "\n".join(clean(text))
    hs = headings(body.split("\n"))
    return {"rfc": n, "source": url, "untrusted_external_text": True, "total_chars": len(body), "offset": offset,
            "returned_chars": len(body[offset:offset + max_chars]), "has_more": offset + max_chars < len(body),
            "sections": [{"number": a, "title": b} for _, a, b in hs if b != "Table of Contents"], "text": body[offset:offset + max_chars]}


def get_section(number, section: str, max_chars: int = 20000) -> dict:
    n, url, text = load_rfc(number)
    lines = clean(text)
    hs = headings(lines)
    want = section.strip().rstrip(".").lower()
    if not want or len(want) > 200 or not (1 <= max_chars <= 50000):
        raise RfcError("section must be 1-200 chars; max_chars 1..50000")
    pick = next((h for h in hs if h[1].lower() == want), None) or next((h for h in hs if want in h[2].lower()), None)
    if not pick:
        raise RfcError(f"section {section!r} not found; call get_rfc to list sections")
    idx = hs.index(pick)
    dp = depth(pick[1])
    end = len(lines)
    for j in range(idx + 1, len(hs)):
        if depth(hs[j][1]) <= dp: end = hs[j][0]; break
    body = "\n".join(lines[pick[0]:end]).strip("\n")
    return {"rfc": n, "source": url, "untrusted_external_text": True, "section": f"{pick[1]} {pick[2]}".strip(),
            "truncated": len(body) > max_chars, "text": body[:max_chars]}


def _index() -> list[tuple[int, str]]:
    url = f"https://{HOST}/rfc-index.txt"
    text = strip_hidden(_cached(url, MAX_INDEX_BYTES))   # every string a tool returns passes the hidden-character stripper (review H2-4)
    entries, cur = [], None
    for line in text.replace("\r", "").split("\n"):
        m = re.match(r"^([0-9]{4,5}) (\S.*)$", line)
        if m:
            if cur: entries.append(cur)
            cur = [int(m.group(1)), m.group(2).strip()]
        elif cur is not None and line.startswith("     "):
            cur[1] += " " + line.strip()
        elif cur is not None and not line.strip():
            entries.append(cur); cur = None
    if cur: entries.append(cur)
    return [(n, t) for n, t in entries]


def search(query: str, limit: int = 10) -> dict:
    terms = [t for t in re.findall(r"[a-z0-9][a-z0-9+\-./]*", query.lower())]
    if not 1 <= len(terms) <= 8 or len(query) > 200 or not (1 <= limit <= 50):
        raise RfcError("query must contain 1-8 words (max 200 chars); limit 1..50")
    hits = []
    for n, t in _index():
        low = t.lower()
        if all(w in low for w in terms):
            status = re.search(r"\(Status: ([^)]+)\)", t)
            title = re.split(r"\.\s+(?=[A-Z][A-Za-z.\- ,]+(?:,|\.\s+[A-Z][a-z]+ [0-9]{4}))", t, maxsplit=1)[0]
            hits.append({"rfc": n, "title": title[:160], "status": status.group(1) if status else "", "entry": t[:400]})
    hits.sort(key=lambda h: -h["rfc"])   # newest first
    return {"source": f"https://{HOST}/rfc-index.txt", "untrusted_external_text": True, "query": strip_hidden(query),
            "total_matches": len(hits), "results": hits[:limit]}
