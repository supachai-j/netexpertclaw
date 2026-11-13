# Import review: fwrule-analyzer (+ fwrule MCP)

Skill: NetClaw `workspace/skills/fwrule-analyzer/SKILL.md` @ cfafa46c (Apache-2.0). Server: AutomateIP/fwrule-mcp @ 3bd52d79 (2026-03-26; pyproject declares Apache-2.0; **the repo has no LICENSE file** - declared licence only).

Reviewed by Hermes-EzAgent 2026-11-13 (read of source; labels: VERIFIED = grep/ran, INTERPRETIVE = inference):
- VERIFIED: `src/` (~13.6k lines incl. parsers) has no `requests/httpx/urllib/socket/subprocess/os.system/eval/exec/open(`; only env use is log level and fastmcp flags. No network or file access.
- VERIFIED: runs under our pinned launch (uv `--no-project --isolated`, fully pinned requirements.txt, git commit pin); `tools/list` returns 4 tools; `list_supported_vendors` answers. Tools: analyze_firewall_rule_overlap, batch_analyze_overlap, list_supported_vendors, parse_policy - all analysis only.
- VERIFIED: upstream FortiOS parser is already in the pinned commit; we dropped NetClaw's instruction to install from a personal fork (supply chain).
- Changes vs upstream skill: removed fork/install instructions and GAIT line, removed cross-references to skills that are not in this repo, documented the 4th tool, added data-handling rule.
- RESIDUAL RISK: requirements.txt pins versions but has no hashes (transitive packages come from PyPI at first launch); PAN-OS XML parsing uses stdlib ElementTree with a regex DOCTYPE strip (upstream comment) - INTERPRETIVE, not fuzzed. Firewall configs passed to the tool/LLM can be sensitive (PDPA): sanitize first.
- Skill risk: read. No device access, so no approval gate needed.
