# Getting started

## Requirements

- Python 3 (tested with 3.12) and [`uv`](https://docs.astral.sh/uv/). The MCP servers are launched with `uv run --no-project --isolated`, so the first start downloads pinned packages.
- git, and at least one supported agent: Claude Code, Codex CLI, Hermes Agent, OpenClaw (needs Node 24.16 or newer) or thClaws.
- Linux. Only Ubuntu 24.04 x86_64 has been tested.

## Install with the netpaw CLI

```bash
git clone https://github.com/supachai-j/netpaw.git ~/netpaw && cd ~/netpaw
bin/netpaw doctor      # uv, python, detected agents
bin/netpaw agents      # supported agents and whether each is tested
bin/netpaw profiles    # minimal | standard | online | full
bin/netpaw list        # skills with risk, maturity and network egress
```

Dry run first (default), then apply:

```bash
bin/netpaw install -a codex hermes -p standard --root "$PWD"
bin/netpaw install -a codex -p standard --root "$PWD" --with-mcp --apply
bin/netpaw uninstall --apply
```

- **Dry run is the default.** Nothing is written without `--apply`.
- `--with-mcp` edits the agent's own config for Codex (`config.toml`), Hermes (`config.yaml`) and thClaws (project `.thclaws/mcp.json`). It keeps one backup per file (`*.bak-netpaw`, mode 0600) and only adds entries it owns. Backups can contain secrets from your original config; delete them when you are done.
- A manifest at `~/.netpaw/manifest.json` records a hash of every installed file; `uninstall` leaves files you edited.
- Profiles: `minimal` (subnet-calculator), `standard` (+ fwrule-analyzer, eve-lab-topology-design), `online` (adds rfc-lookup and wikipedia-research, which use the internet), `full` (everything). Add single skills with `-s <skill>`.
- Agents the installer knows but we have **not** tested (`.agents/skills`, opencode, Cursor, Gemini CLI) need `--allow-untested`.
- There is no `pip install netpaw` or `npx netpaw`; do not install a package with that name.

## Per-agent notes

**Claude Code** - load the plugin from the clone:

```bash
claude --plugin-dir ~/netpaw
```

You should see the skills as `netpaw:<skill>` and the MCP servers connected. The marketplace route (`/plugin marketplace add supachai-j/netpaw`, `/plugin install netpaw`) is untested. If you open Claude Code inside the repo itself, one server shows `failed` because the root `.mcp.json` is read as a project file; the plugin copy is unaffected.

**Codex CLI** - `netpaw install -a codex ... --with-mcp --apply`. Codex calls tools by namespace (`mcp__subnet_calc`); just describe the goal. Our read-only tools carry `readOnlyHint`, which `codex exec` requires. At cold start Codex may list only some servers for the first turns; retry.

**Hermes Agent** - `netpaw install -a hermes ... --with-mcp --apply`, then `hermes skills list` and `hermes mcp test subnet-calc`. Hermes must be installed with its official installer, not pip.

**OpenClaw** - install skills with `openclaw skills install dist/openclaw/skills/<name>` and add each server with `openclaw mcp set <name> '<json>'` (one server object, not the whole `mcpServers` block). The model reaches MCP tools through `tool_search` then `dispatch_action`.

**thClaws** - project-level: `netpaw install -a thclaws ... --project --with-mcp --apply`. thClaws asks you to approve each stdio server once. `-p` (headless) does not ask again for tool calls.

Manual route without the CLI: `python3 scripts/build.py --root "$PWD"` writes agent-specific files to `dist/`; copy them as described by `docs/RUNTIME-MATRIX.md`.

## Check it works

Ask: *"Are 192.0.2.10 and 192.0.2.70 on the same /26?"* The agent should call `same_subnet` and answer **no** (192.0.2.0/26 and 192.0.2.64/26). If it answers without calling a tool, the answer may still be right, but you have not verified the skill is wired; look at the agent's tool-call log.
