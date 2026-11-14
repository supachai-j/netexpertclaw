# Roadmap

Ordered by evidence, not by wish. The detailed, checkable list is `docs/ROADMAP.md`.

1. **Make the current skills measurably useful.** Trigger evaluation 3 runs per query on every skill; output evaluation with versus without the skill; a fix for hidden tools at Codex cold start.
2. **Real-model runs per agent** (needs a person to log in to the agent on a test machine). Until then every agent other than Claude Code stays at mock-model evidence.
3. **Project hygiene:** stable install directory for MCP config instead of a checkout, hash-pin the tool-definition cache with CODEOWNERS protection, fuzz the fwrule XML parsers, scheduled skill scanning in CI.
4. **More read-only skills** from NetClaw by wave: offline tools, public-internet lookups (needs multi-host egress policy), then read-only access to devices with credentials.
5. **Write skills** only after a server-side gate exists: change request, baseline, approval bound to device and payload, verify, audit, with tests against a lab.
6. **More agents:** tested installs for `.agents/skills`, opencode, Cursor, Gemini CLI; Windows and macOS.

Not planned: tools that open listening ports, accept arbitrary CLI text, or write configuration without a gate.
