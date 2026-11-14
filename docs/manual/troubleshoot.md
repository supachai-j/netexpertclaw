# Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| MCP server shows `failed` on first start | first start downloads packages, or `uv` is missing | `uv --version`; check network; run the server command from the install snippet by hand |
| Codex: `MCP tool call requires approval, but approval policy is never` | the tool lacks `readOnlyHint` | run `tests/smoke_mcp.py` to check annotations; our tools set it |
| Codex lists only some MCP tools in the first turns | cold start; the agent does not wait for servers (cause not fully known) | retry the prompt; report it with the Codex version |
| thClaws `mcp spawn refused ... not in the user allowlist` | args or directory changed, or first run was headless | open the REPL and approve again |
| OpenClaw does not list tools directly | by design | the model uses `tool_search` then `dispatch_action` |
| OpenClaw installs an old version | Node 22 | use Node 24.16 or newer |
| Hermes: duplicate `mcp_servers:` | appended to an existing block | merge by hand |
| `subnet_calculator` error `host bits set` | input like `192.0.2.5/26` | use the network address `192.0.2.0/26` |
| fwrule: `tool list changed upstream; regenerate tools cache` | live tool list differs from `tools.cache.json` | intended stop; run `scripts/gen_tools_cache.py fwrule`, review the diff, then commit |
| fwrule: `tool set changed` from the launcher | upstream added a tool | intended stop; review it and update `REVIEWED` in `mcp/fwrule/launch.py` |
| fwrule: `XML DOCTYPE/ENTITY declarations are not accepted` | the payload contains `<!DOCTYPE` or `<!ENTITY` | remove them; legitimate device configs do not need them |
| fwrule: ruleset rejected as too large | proxy caps rulesets at 4 MiB | lower `FOMC_MAX_RULESET_BYTES` if you want smaller; do not exceed upstream's 64 MiB |
| rfc-lookup / wikipedia: `response too slow` or size error | slow or oversized response | retry later; limits are 15 s and a few MB by design |
| lint: `uv run needs --no-project --isolated ...` | server entry breaks the rule | copy the pattern in [develop](develop.html) |
| lint: `declare egress explicitly` or `import network modules but egress is []` | a server needs an `egress` entry | list the hosts, or remove the network import |
| `dist/` has paths from another machine | built with another `--root` | rebuild with this machine's `--root` |

## Leftovers after uninstall

- thClaws: `netpaw uninstall` removes skills and its `.thclaws/mcp.json` entries but not thClaws' own `~/.config/thclaws/mcp_allowlist.json`; delete the netpaw lines yourself.
- `*.bak-netpaw`: one backup per edited config (state before the first netpaw edit, mode 0600). It may contain secrets from your original config; delete it when you no longer need it.

Still stuck: open an issue with the exact command and output. Never attach customer data or credentials.
