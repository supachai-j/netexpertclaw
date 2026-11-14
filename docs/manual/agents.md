# Supported agents

Levels: **L1** the agent sees the skill, **L2** it accepts the MCP config, **L3** it starts the server and lists the tools, **L4** a model calls a tool through the agent and the result comes back. "Mock" means a local fake model that issues one scripted tool call, which proves the agent-to-server path, not that a real LLM chooses the skill.

| Agent | Version tested | Levels | Model |
|---|---|---|---|
| Claude Code | 2.1.322 | L1-L4 | real |
| Hermes Agent | v0.23.1 | L1-L3 | not run for L4 |
| Codex CLI | 0.169.0 | L1-L4 | mock |
| thClaws | 0.156.0 | L1-L4 | mock |
| OpenClaw | 2026.11.3 | L1-L4 | mock |

Tested on Ubuntu 24.04 x86_64. Windows and macOS have not been tried. Raw commands and output: `docs/CONFORMANCE.md`. Later re-tests with five servers installed found: thClaws and OpenClaw call wikipedia correctly; Codex sometimes showed none of the MCP tools in the first turns (cause unknown), and wikipedia on Codex is unproven.

## Per-agent behaviour worth knowing

| Agent | Notes |
|---|---|
| Claude Code | Skills appear as `netpaw:<skill>`; MCP as `plugin:netpaw:<server>`. Opening the repo itself shows one `failed` server from the root `.mcp.json` (harmless). |
| Codex | Tool names are namespaced `mcp__<server>` (dashes become `_`). `exec` refuses tools without `readOnlyHint`. Cold start may hide tools for the first turns. |
| Hermes | Install with the official installer, not pip. Merge `mcp_servers:` by hand if you already have the block. |
| OpenClaw | Needs Node 24.16+ (Node 22 silently installs an old version). `mcp set` takes one server object. Tools are reached via `tool_search` then `dispatch_action`; results are wrapped as external untrusted content. |
| thClaws | Approval of an stdio server is tied to the full command line and working directory. `-p` runs no slash commands and does not re-ask. Linux `--cli` needs `libwebkit2gtk-4.1-0 libsoup-3.0-0 libjavascriptcoregtk-4.1-0`. |

## Other agents

Anything that reads the open `SKILL.md` layout can use the skill text, and anything that speaks MCP over stdio can use the servers. The installer has targets for the shared `.agents/skills` directory, opencode, Cursor and Gemini CLI, but they are **untested** and refused without `--allow-untested`. If you try one, open a PR or issue with the version, the commands and what you saw (see [develop](develop.html)); that is the quickest way to move it to the tested list.
