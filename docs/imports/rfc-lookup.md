# rfc-lookup - review note (NOT an import: independent reimplementation)
Upstream candidate: NetClaw skill `rfc-lookup` -> `npx -y @mjpitz/mcp-rfc` (npm, Apache-2.0, single maintainer, latest 0.2504.4 from 2025-04-11).
Read on 2026-11-13 (tarball sha512 matched the registry integrity; 2 source files, 560 lines):
- VERIFIED: runtime deps are `@modelcontextprotocol/sdk ^1.9.0`, `axios ^1.8.4`, `jsdom ^26.0.0` with caret ranges and no lockfile in the package; the skill launches it with `npx -y` (unpinned fetch-and-run on every start). No repository URL in package metadata.
- VERIFIED: RFC number is interpolated into the URL without validation (`.../rfc${number}.txt`); no request timeout, no response size cap; axios follows redirects.
- VERIFIED: egress is only www.ietf.org and www.rfc-editor.org; no fs writes, no child_process, no eval in the two source files (grep + read).
- INTERPRETIVE: jsdom/axios bring a large transitive tree whose supply chain we would have to pin and audit for a text-fetching tool.
Decision (D-9): do not run the npm package. `mcp/rfc-lookup/` is an original stdlib-only Python server with the same tool names (get_rfc, get_rfc_section, search_rfcs). No upstream code was copied; the SKILL.md is newly written. Attribution for the tool surface is in the skill text.
Controls in the reimplementation (tests/test_rfc.py, 15 tests, 13 offline with synthetic fixtures): digits-only number (1-5), host allow-list www.rfc-editor.org over https only, redirects refused, content-type must be text/plain, 15 s timeout, 5 MB / 4 MB body caps, in-memory cache only, results flagged `untrusted_external_text`, paging limits, `readOnlyHint` + `openWorldHint`, `egress` declared in mcp/servers.json and linted.
NOT checked: behaviour against every RFC (old centered-heading RFCs list only some sections; documented), rfc-editor.org availability/rate limits, any hostile content other than a synthetic prompt-injection sample.
