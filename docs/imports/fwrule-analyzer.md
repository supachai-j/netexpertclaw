# Import review: fwrule-analyzer (+ fwrule MCP)

Skill: NetClaw `workspace/skills/fwrule-analyzer/SKILL.md` @ cfafa46c (Apache-2.0). Server: AutomateIP/fwrule-mcp @ 3bd52d79 (2026-03-26; pyproject declares Apache-2.0; **the repo has no LICENSE file** - declared licence only).

Reviewed by the build agent 2026-11-13 (read of source; labels: VERIFIED = grep/ran, INTERPRETIVE = inference):
- VERIFIED: `src/` (~13.6k lines incl. parsers) has no `requests/httpx/urllib/socket/subprocess/os.system/eval/exec/open(`; only env use is log level and fastmcp flags. No network or file access.
- VERIFIED: runs under our pinned launch (uv `--no-project --isolated`, fully pinned requirements.txt, git commit pin); `tools/list` returns 4 tools; `list_supported_vendors` answers. Tools: analyze_firewall_rule_overlap, batch_analyze_overlap, list_supported_vendors, parse_policy - all analysis only.
- VERIFIED: upstream FortiOS parser is already in the pinned commit; we dropped NetClaw's instruction to install from a personal fork (supply chain).
- Changes vs upstream skill: removed fork/install instructions and GAIT line, removed cross-references to skills that are not in this repo, documented the 4th tool, added data-handling rule.
- RESIDUAL RISK: requirements.txt pins versions but has no hashes (transitive packages come from PyPI at first launch); PAN-OS XML parsing uses stdlib ElementTree with a regex DOCTYPE strip (upstream comment) - INTERPRETIVE, not fuzzed. Firewall configs passed to the tool/LLM can be sensitive (PDPA): sanitize first.
- Skill risk: read. No device access, so no approval gate needed.

- Added `mcp/fwrule/launch.py`: upstream tools carry no MCP annotations; Codex `exec` refuses unannotated tools (see docs/CONFORMANCE.md C-8). The launcher sets readOnlyHint on the 4 reviewed tools and exits if the tool set changes (fail closed).

## Lazy proxy (`mcp/fwrule/proxy.py`, added for Codex)
Codex `exec` drops a server that answers `initialize` late (the runtime-test agent measured: a 2 s delay already loses the tools). fwrule needs ~1.8 s even with a prebuilt venv (FastMCP/pydantic import), more on a cold cache. `proxy.py` (stdlib, ~100 lines) answers `initialize`/`tools/list`/`ping` at once (measured 0.03 s) from `tools.cache.json` and starts the real server on the first other request (first call done in ~0.9 s here).
- VERIFIED by tests/test_proxy.py: cache sha256 integrity; initialize/list served without starting the child; `tools/call` params and result forwarded unchanged (unicode included); a live tool list that differs from the cache makes every call fail closed with an error and a stderr line; a tampered cache refuses to start; committed cache == live server (`scripts/gen_tools_cache.py fwrule --check`).
- Child environment is allow-listed (PATH, HOME, LANG, TMPDIR, XDG_*, SSL_CERT_*, UV_*); no shell; argv list only.
- Regenerate the cache after any bump of the fwrule pin: `uv run --with mcp==1.30.0 python scripts/gen_tools_cache.py fwrule`, re-review the diff of the tool list, commit.
- NOT verified: that Codex now registers fwrule (needs the runtime-test agent's cold-cache run on worker-A); behaviour with clients that use server notifications or `tools/list_changed` (this server does not emit them).

## Security review H2 follow-up
H2-1 (PAN-OS DOCTYPE strip bypass by nesting, upstream @3bd52d7 parser.py): the netpaw proxy now rejects any tool argument containing `<!DOCTYPE`, `<!ENTITY`, `<!ELEMENT`, `<!ATTLIST` or `<!NOTATION` (case-insensitive, whitespace tolerant, searched through nested arguments) with -32602 before the child starts, and sets `FOMC_MAX_RULESET_BYTES` to 4 MiB for the child (user may lower it via the environment; default upstream 64 MiB). Not fixed upstream; the owner decides whether to report it to the upstream project. Tests: tests/test_hardening.py (Review2).
