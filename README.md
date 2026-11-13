# netexpertclaw

Network-engineering skills + MCP tool packs that run on multiple agent runtimes from **one source of truth**.

Targets: Claude Code · Codex · Hermes Agent · OpenClaw · thclaw

Inspired by [automateyournetwork/netclaw](https://github.com/automateyournetwork/netclaw) (Apache-2.0). Ideas only; code reuse must keep license + attribution (see NOTICE).

Status: P0 done (runtime research). See [docs/PLAN.md](docs/PLAN.md), [docs/RUNTIME-MATRIX.md](docs/RUNTIME-MATRIX.md).

## Install
Claude Code: `/plugin marketplace add supachai-j/netexpertclaw` then `/plugin install netexpertclaw --marketplace supachai-j/netexpertclaw` (private repo: needs git credentials).
Other runtimes: `python3 scripts/build.py --root <clone path>` then copy `dist/<runtime>/` (see docs/RUNTIME-MATRIX.md). Requires `uv`.

## Dev
`python3 scripts/lint.py && python3 -m unittest discover -s tests && uv run --with "mcp>=1.2,<2" python tests/smoke_mcp.py`

Known quirk: opening Claude Code *inside* this repo also reads the root `.mcp.json` as a project server (shows `failed`, `${CLAUDE_PLUGIN_ROOT}` unresolved). The plugin copy connects fine. Harmless.
