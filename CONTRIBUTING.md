# Contributing
Thanks for helping. This project packages network-engineering skills + MCP tools for several agent runtimes from one source. Read `docs/AI-SDLC.md` (process) and `docs/SECURITY-REVIEW.md` (threat model) first.

**Ground rules**
- Open an issue before large changes. One topic per PR. Target `main`; CI (`ci`, `security`) must be green.
- No secrets, customer data, real hostnames/IPs or device configs in code, tests, issues or docs. Use documentation ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24, 2001:db8::/32).
- Skills that can change a device must declare `risk: write`, `approval: required`, and the MCP server must enforce baseline -> approval -> verify -> audit itself (see `docs/DECISIONS.md` D-2). Read-only tools must set `readOnlyHint`.
- Imports from other projects go through `scripts/import-netclaw.py` with a pinned commit, a review note in `docs/imports/`, and a license check.
- Pin dependencies (versions + hashes) and GitHub Actions (commit SHA). Do not add network calls at import time.
- Claims need evidence: say what you ran and what it printed (see `docs/CONFORMANCE.md` for the style).

**Dev loop**: `bin/netpaw lint && bin/netpaw test && bin/netpaw smoke` (needs `uv`). Live checks: `NETPAW_LIVE_TESTS=1 python3 -m unittest discover -s tests`.

**Licence**: contributions are under Apache-2.0 (inbound = outbound). Sign off commits (`git commit -s`, DCO).
Report vulnerabilities via `SECURITY.md`, not a public issue.
