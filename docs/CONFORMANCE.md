# Runtime conformance (tested on real runtimes)

Scope: no model calls; checks that each runtime loads the generated skill, connects the MCP server and discovers its tools.
Commit under test: f72eaba (main). Worker: hermes-worker-01, isolated HOME, no credentials.

| Runtime | Version | Skill loaded | MCP connected | Tools discovered | Evidence | Tester | Date |
|---|---|---|---|---|---|---|---|
| Claude Code | 2.1.322 | PASS (`netexpertclaw:subnet-calculator`) | PASS (`plugin:netexpertclaw:subnet-calc` connected) | PASS 4 | `claude -p ... --output-format stream-json` init event; tool call answered 192.0.2.0/26 wildcard | Hermes | 2026-11-13 (on e58af2e; unchanged by f72eaba except flags - re-run pending) |
| Hermes | v0.23.1 (2026.9.24) | PASS (`hermes skills list`: subnet-calculator, category netexpertclaw, enabled) | PASS (`hermes mcp test`: Connected 3944ms) | PASS 4 (subnet_calculator, _v6, _auto, same_subnet) | `tests/runtimes/hermes.sh` | Hermes | 2026-11-13 |
| Codex | - | - | - | - | pending (Neo) | | |
| OpenClaw | - | - | - | - | pending (Neo) | | |
| thClaws | - | - | - | - | pending (Neo) | | |

## Findings
- H-1 (docs/script): Hermes `config.yaml` ships `mcp_servers:` only as a comment, so appending the snippet works on a fresh install, but on an existing config with `mcp_servers:` it must be merged by hand. `tests/runtimes/hermes.sh` refuses instead of appending twice.
- H-2: `pip/uv pip install` of hermes-agent from git is blocked by Hermes ("Building wheels... not supported"); the official shell installer is required (used with isolated HOME + `--skip-setup --skip-browser --skip-computer-use`).
- H-3: Hermes shows the skill as category `netexpertclaw` because build.py places it under `skills/netexpertclaw/<name>`; intended.

## Not tested
Model-driven invocation (does the model pick the skill and call the tool) on any runtime other than Claude Code: needs an API login on the worker, which is not copied (Rule 30).
