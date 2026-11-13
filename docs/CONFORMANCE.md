# Runtime conformance (Neo lane), v3 - 2026-11-13 (supersedes v2; adds section "Added in v3")

Pin: repo commit `f72eaba07e8fa63261238aa21d12fc7c61fcd92c` (tarball sha256 `ac3a6dc397356923...`; v1 of this report used `e58af2e`).
Built on each worker with `python3 scripts/build.py --root /home/ubuntu/nec-conf/f72`; `grep -rn /home/ dist/` found only that root (C-1 fixed upstream).
Workers: tumps-render-03 (.71: Codex, thClaws), tumps-render-04 (.72: OpenClaw). Python 3.12.3. Isolated `HOME=~/nec-conf/home`.
No credentials, no cloud model, no API key on any worker.

Levels (skill `agent-skill-runtime-conformance`): L1 skill discovered, L2 config accepted, L3 runtime spawned the server and listed tools,
L4 a model turn made a tool call that went through the runtime and the real result came back.
**L4 here is driven by a local MOCK model endpoint** (`tests/runtimes/mock_model.py`, 127.0.0.1 only, scripted: it emits one `same_subnet` call, then quotes the result).
It proves the runtime -> MCP path end to end. It does NOT prove a real LLM picks the tool or follows the SKILL.md text.

## Matrix (pin f72eaba)

| Runtime | L1 skill | L2 config | L3 runtime spawns + lists | L4 tool call via mock model |
|---|---|---|---|---|
| Codex CLI 0.169.0 | VERIFIED `codex debug prompt-input` lists `subnet-calculator` (`r0/subnet-calculator/SKILL.md`) | VERIFIED `codex mcp get subnet-calc` shows new args (`--no-project --isolated --with mcp==1.30.0`) | covered by L4 | **VERIFIED, but only with annotations** (C-8): stock server -> `MCP tool call requires approval, but approval policy is never` (failed); server with `readOnlyHint` -> `status: completed`, result `same_subnet: true, 192.0.2.0/24` |
| thClaws 0.156.0 | VERIFIED REPL `/skills` -> `subnet-calculator (project)` (v1 run; same files) | VERIFIED | VERIFIED after interactive approval; `/mcp` -> 4 tools | VERIFIED `[tool] subnet-calc__same_subnet {...}` then result `same_subnet: true` (run with `--accept-all`, provider `openai-compat`, model `oai/mock`) |
| OpenClaw 2026.11.3 | VERIFIED `skills info` -> Ready, Visible to model: yes, `uv` found | VERIFIED `mcp set` | VERIFIED `mcp probe` -> 4 tools | VERIFIED via `tool_search` then `dispatch_action` (C-12); result `same_subnet: true` returned, wrapped as EXTERNAL_UNTRUSTED_CONTENT |
| Generic stdio check (all generated configs) | n/a | n/a | VERIFIED `mcp_stdio_check.py`, 0.62 s on f72 | n/a |

Repo's own checks on the worker at pin f72eaba (Python 3.12.3): `unittest discover -s tests` **22/22 OK**; `scripts/lint.py` -> `lint ok (1 skill(s), 1 server(s))`; `tests/smoke_mcp.py` ok (`uv run --no-project --isolated --with mcp==1.30.0`).
Claude Code and Hermes adapters: Hermes lane.

## Added in v3 (all VERIFIED on the workers, pin f72eaba, mock model, no credentials)

### F-8 (uv runs the project's build backend from cwd): reproduced through each runtime, and the fix works in each
Trap: a directory whose `pyproject.toml` points at a local build backend that only writes a marker file (harmless, same idea as SECURITY-REVIEW `repro_uv_cwd.sh`).
Each runtime was started with cwd = trap dir.

| Runtime | MCP child cwd | old args (no `--no-project --isolated`) | f72eaba args |
|---|---|---|---|
| Codex 0.169.0 (`codex exec` from trap dir) | session cwd | **backend EXECUTED** (marker written) | not executed; tool call completed |
| thClaws 0.156.0 (REPL in trap dir) | project dir (`[cwd:...]`) | **backend EXECUTED**, server failed to start | not executed; 4 tools |
| OpenClaw 2026.11.3 (`mcp probe` from trap dir) | process cwd | **backend EXECUTED**, server failed to start | not executed; 4 tools |

So the cwd inheritance premise of F-8 holds for all three, and `--no-project --isolated` closes it for all three. Any new server entry must keep both flags (add a lint rule for `uv run` without `--no-project`).

### Approval gate for a WRITE tool: runtimes do not agree (matters for P4)
Toy server `tests/runtimes/toy_write_server.py` (no device; `apply_change` only creates a marker file; annotated `readOnlyHint=false, destructiveHint=true`; `read_state` is read-only). Mock model asks for `apply_change`. Unattended = no human at the runtime.

| Runtime / mode | Result |
|---|---|
| Codex `exec` (default) | **BLOCKED**: `MCP tool call requires approval, but approval policy is never`; marker absent. Fail-closed. |
| thClaws `-p` (headless), default permissions | **EXECUTED** unattended, marker present (banner `permissions=auto`) |
| thClaws `-p --permission-mode ask` | **EXECUTED** unattended, marker present (banner `permissions=ask`: ask mode does not stop a headless run) |
| thClaws interactive REPL, `--permission-mode ask` | Prompts `[approval] toy-write__apply_change input={...} [y]es / [n]o / yolo`; answering `n` -> marker absent |
| OpenClaw `agent --local` (embedded, no gateway) | **EXECUTED** unattended via `dispatch_action`, marker present |

Meaning: only Codex exec fail-closes on its own. thClaws headless and OpenClaw local run an MCP write tool without asking, whatever the annotations say.
Do not rely on the runtime's approval UI or on `readOnlyHint`/`destructiveHint` as the control for write tools. The control must live in the MCP server
(baseline -> change-request id -> verify -> audit, refuse when the approval token is missing), as SECURITY-REVIEW F-4/F-9 and the upstream design already say.
Interactive approval prompts in OpenClaw's gateway/chat postures were not tested (no gateway on the worker).

## Findings still open on f72eaba

- **C-8 (confirmed with evidence): MCP tools need `readOnlyHint`.** Without annotations, Codex refuses the call in `codex exec`
  (approval policy `never`): `MCP tool call requires approval, but approval policy is never`. Adding
  `ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)` to all four tools (patch: `annotations-readonly.patch`)
  made the same call complete. OpenClaw `mcp probe` also warns "tools have no safety annotations". f72eaba has no `readOnlyHint`.
  This is also the mechanism for SECURITY-REVIEW F-4/F-9: the server states read vs write, the runtime enforces. Write tools must NOT carry `readOnlyHint`.
- **C-3 thClaws re-approval (confirmed again).** New args from the F-8/F-10 fixes changed the command line, so the old allowlist entry no longer matched: headless run
  refused, interactive `y` stored a new entry `... --no-project --isolated --with 'mcp==1.30.0' ... [cwd:<dir>]`. Every upgrade that changes args or install path needs re-approval; document it.
  Docs (thclaws.cloud manual ch05) say the key is `command` only; observed 0.156.0 stores the whole command line + cwd. Observed behaviour trusted.
- **C-4/C-5** thClaws `-p` does not run slash commands (they go to the model); `--cli` needs libwebkit2gtk-4.1 at load. Unchanged.
- **C-6** OpenClaw 2026.11.3 needs Node >= 24.16 (tested on 24.22.3). On Node 22 npm silently gives 2026.9.2. Unchanged.
- **C-7** OpenClaw `mcp set` takes the inner server object, not the `{"mcpServers":...}` snippet. Unchanged.
- **C-12 OpenClaw calls MCP tools indirectly.** The model sees only core tools plus `tool_search`, `tool_describe`, `dispatch_action`. MCP tools are discovered with
  `tool_search`, then run with `dispatch_action {"id":"mcp:<server>:<server>__<tool>","args":{...}}`. A skill that says "call `same_subnet`" works only if the model follows
  that search-then-dispatch path. Not tested with a real model.
- **C-13 Codex tool naming.** Codex advertises MCP tools as a namespace `mcp__subnet_calc` (server name `-` -> `_`) containing `same_subnet`. Skill text must not hardcode a prefix.
- **C-14 thClaws tool naming.** `subnet-calc__same_subnet`.

## Fixed upstream since v1 (verified on the worker)
- C-1 (stale absolute paths): dist built fresh, no foreign paths.
- F-8: args now include `--no-project --isolated` (seen in `codex mcp get` and the thClaws prompt).
- F-10: `mcp==1.30.0` pinned (server reports 1.30.0).
- C-2 (PyPI needed at first run) remains: cold start still resolves from the package index.

## Not tested
1. A real LLM turn in any runtime (needs credentials; Rule 30: agents do not copy tokens to workers). Mock endpoint only.
2. A real write tool against a device (none exists; the toy server only writes a marker file).
3. Hermes adapter (Hermes lane). Codex `agents/openai.yaml` effect (not tested). OpenClaw gateway/chat approval postures (no gateway on the worker).
4. Windows/macOS hosts (all runs on Ubuntu 24.04, x86_64).

## Reproduce
`tests/runtimes/mcp_stdio_check.py <config>` (stdlib). `tests/runtimes/mock_model.py [port]` (env `MOCK_LOG`, `MOCK_SEQ` multi-step chat script, `MOCK_DUMP`).
- Codex: add `[model_providers.mock] base_url="http://127.0.0.1:9911/v1" wire_api="responses"` and `model_provider="mock"`; `codex exec --skip-git-repo-check --json "<prompt>"`.
- thClaws: `OPENAI_COMPAT_BASE_URL=http://127.0.0.1:9911/v1 OPENAI_COMPAT_API_KEY=<any> thclaws -m oai/mock --no-session --accept-all -p "<prompt>"` (after approving the MCP command once in a pty).
- OpenClaw: `openclaw config set models.providers.mock '{"baseUrl":"http://127.0.0.1:9911/v1","api":"openai-completions","apiKey":"x","models":[{"id":"mock","name":"mock"}]}' --strict-json`,
  `openclaw config set agents.defaults.model.primary mock/mock`, `MOCK_SEQ='[["tool_search",{"query":"same_subnet"}],["dispatch_action",{"id":"mcp:subnet-calc:subnet-calc__same_subnet","args":{...}}]]'`,
  `openclaw agent --local --agent main --session-key agent:main:<unique> -m "<prompt>"` (fresh session key per run: OpenClaw keeps history and the script counts tool results in it).

## Still installed on workers (single root `~/nec-conf` each; remove only after owner OK)
- .71: `~/nec-conf` (thClaws v0.156.0, Codex 0.169.0, venv/uv; mock endpoint stopped); apt: `libwebkit2gtk-4.1-0 libsoup-3.0-0 libjavascriptcoregtk-4.1-0` (+deps).
- .72: `~/nec-conf` (OpenClaw 2026.11.3, user-space Node 24.22.3, venv/uv; mock endpoint stopped).
- No daemon left running; port 9911 closed on both; trap dirs and marker files removed. OpenClaw/Codex configs inside `~/nec-conf/home` still contain the mock provider and the toy-write server (isolated HOME, goes with `rm -rf ~/nec-conf`).

## Hermes lane (Hermes-EzAgent, 2026-11-13)

| Runtime | L1 skill | L2/L3 MCP | L4 |
|---|---|---|---|
| Hermes v0.23.1 (2026.9.24), worker hermes-worker-01, isolated HOME | VERIFIED `hermes skills list` -> subnet-calculator (category netexpertclaw, enabled) | VERIFIED `hermes mcp test subnet-calc`: Connected, 4 tools (`tests/runtimes/hermes.sh`) | not run (no model) |
| Claude Code 2.1.322 | VERIFIED `netexpertclaw:subnet-calculator` in init event | VERIFIED `plugin:netexpertclaw:subnet-calc` connected | VERIFIED with a real model turn: tool call answered wildcard of 192.0.2.0/26 (on e58af2e; not re-run on later pins) |

- H-1 Hermes config: if `mcp_servers:` already exists in config.yaml the snippet must be merged by hand; hermes.sh refuses instead of appending twice.
- H-2 `pip/uv pip install` of Hermes from git is blocked by Hermes; use the official shell installer (isolated HOME, `--skip-setup --skip-browser --skip-computer-use`).

## Resolution of Neo's findings (commit after f72eaba)
- C-8 FIXED: `readOnlyHint` etc. on all subnet-calc tools (Neo's patch applied); imported `fwrule` server wrapped by `mcp/fwrule/launch.py` which annotates its 4 reviewed tools and fails closed if the tool set changes. `tests/smoke_mcp.py` now asserts every tool of a `capability: read` server carries `readOnlyHint`. Needs a Codex re-run on the new pin to confirm L4 for both servers (pending).
- C-3 (thClaws re-approval on arg change), C-6, C-7, C-12, C-13, C-14: documentation items, unchanged; skill text must not hardcode tool-name prefixes (checked: none in SKILL.md files).
