# netexpertclaw

Network-engineering skills + MCP tool packs that run on multiple agent runtimes from **one source of truth**.

Targets: Claude Code · Codex · Hermes Agent · OpenClaw · thclaw

Inspired by [automateyournetwork/netclaw](https://github.com/automateyournetwork/netclaw) (Apache-2.0). Ideas only; code reuse must keep license + attribution (see NOTICE).

Codename / CLI: **nxc** (`bin/nxc`; run `bin/nxc doctor`, `bin/nxc list`, `bin/nxc install <runtime>`). Not put on PATH: NetExec also ships a command called `nxc`.

Status: P0 done (runtime research). See [docs/PLAN.md](docs/PLAN.md), [docs/RUNTIME-MATRIX.md](docs/RUNTIME-MATRIX.md).

## Install
Claude Code: `/plugin marketplace add supachai-j/netexpertclaw` then `/plugin install netexpertclaw --marketplace supachai-j/netexpertclaw` (private repo: needs git credentials).
Other runtimes: `python3 scripts/build.py --root <clone path>` then copy `dist/<runtime>/` (see docs/RUNTIME-MATRIX.md). Requires `uv`.

## Dev
`python3 scripts/lint.py && python3 -m unittest discover -s tests && uv run --with "mcp>=1.2,<2" python tests/smoke_mcp.py`

Known quirk: opening Claude Code *inside* this repo also reads the root `.mcp.json` as a project server (shows `failed`, `${CLAUDE_PLUGIN_ROOT}` unresolved). The plugin copy connects fine. Harmless.

## Imported from NetClaw
`python3 scripts/import-netclaw.py [--upstream <checkout>]` re-creates imported skills from `imports/netclaw.json` (pinned commit, exact-match edits, hashed requirements, NOTICE entries). Per-import review: `docs/imports/`. Imported so far: `fwrule-analyzer` (+ `fwrule` MCP pinned to AutomateIP/fwrule-mcp@3bd52d79).

## Manual (website)
Source: `docs/manual/*.md` (Thai). Build: `pip install markdown && python3 scripts/build_site.py` -> `site/` (static). Pages: overview, install per runtime, usage, skills/tools, safety, develop, compatibility, troubleshooting.

## Manual (public)
https://supachai-j.github.io/netexpertclaw-docs/ (source: public repo supachai-j/netexpertclaw-docs; this repo keeps docs/manual as the source of truth - copy changes over, see docs/DECISIONS.md D-5).
