# wikipedia-research - review note (NOT an import: independent reimplementation)
Upstream: NetClaw skill `wikipedia-research` (246 lines, Apache-2.0) calling an external FastMCP server (`Wikipedia_MCP`) whose requirements install the PyPI `wikipedia` 1.4.0 scraper plus fastmcp/mcp (config/python-components/wikipedia.txt, NetClaw @cfafa46c). Read 2026-11-14 (SKILL.md, the component requirement file and the recorded install log; the upstream server source is not in the NetClaw tree I checked).
- VERIFIED: tool surface = search_pages, get_summary, get_content, get_references, get_categories, plus an existence check, each taking `{"input": {...}}`.
- VERIFIED: the install log shows `wikipedia-1.4.0.tar.gz` built from `setup.py` (sdist, build-time code execution) with a large transitive tree.
- INTERPRETIVE: the `wikipedia` package is an HTML scraper with a long-unmaintained release line; I did not audit it and chose not to depend on it.
Decision (D-11): reimplement with the official MediaWiki Action API using stdlib only. Same tool names (existence is reported by `get_summary` as "page not found"). Egress: `en.wikipedia.org/w/api.php` only; redirects refused (the API resolves page redirects); JSON content type only; 15 s timeout; 3 MB cap; title validation (no `| # < > [ ] { }`); control and invisible characters stripped; results flagged untrusted and carry the CC BY-SA licence note; 16-entry in-memory cache; no files written.
Verified live 2026-11-14: summary (OSPF -> "Open Shortest Path First" redirect), search, paged content, references, categories, disambiguation flag (Mercury), not-found error. Offline tests use synthetic API responses (tests/test_wiki.py); live checks need NETPAW_LIVE_TESTS=1.
NOT checked: behaviour under Wikipedia rate limiting (no retry logic; a 429 is reported as an error), non-English titles, very large pages near the cap, other MediaWiki hosts (not supported on purpose).
Privacy: search words and titles are sent to Wikipedia; the skill tells the model not to include customer or internal names.

## Cross-review fixes (tester role, 2026-11-14)
WK-1 overall 15 s read deadline (not per read; same in rfc-lookup); WK-2 hidden-character stripper broadened (shared); WK-3 malformed API shapes become a normal error; WK-4 only article namespace (ns 0) pages are returned, User:/Talk: etc. refused. Tests: tests/test_hardening.py.
