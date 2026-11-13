# Runtime Matrix (P0 research, 2026-11-13)

Sources: official docs of each runtime (links at bottom). Hermes row from local install.

| | Skill format | Skill path | MCP config | Bundle/Distribute |
|---|---|---|---|---|
| Claude Code | `skills/<n>/SKILL.md` (name, description frontmatter) | `~/.claude/skills/`, `.claude/skills/` | `.mcp.json` (in plugin root or project) | Plugin: `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`; `/plugin marketplace add supachai-j/netexpertclaw` |
| Codex | `SKILL.md` + optional `agents/openai.yaml` (policy.allow_implicit_invocation, dependencies.tools[mcp]) | skills dirs (CLI/IDE/app) ; `$skill` to invoke | `~/.codex/config.toml` or `.codex/config.toml` -> `[mcp_servers.<n>]` (command/args/env_vars, url/bearer_token_env_var); `codex mcp add` | Codex plugins (preferred for distribution) |
| Hermes | `SKILL.md` frontmatter (name, description, version, metadata.hermes) | `~/.hermes/skills/<category>/<n>/` | `config.yaml` -> `mcp_servers:` (command/args/env or url/headers) | copy/`hermes skills` |
| OpenClaw | `SKILL.md` + `metadata: {"openclaw": {requires:{bins,env,config}, primaryEnv, install}}` (single-line JSON) | workspace/skills, `~/.openclaw` ; ClawHub | `openclaw.json` | ClawHub |
| thClaws (thclaws.ai, Rust, Apache-2.0) | `SKILL.md` (name, description, short_description) ; dir name must == name | `.thclaws/skills/`, `~/.config/thclaws/skills/`, **also reads `.claude/skills/`** | `.thclaws/mcp.json` or `.mcp.json` (`mcpServers`, stdio or http); `/mcp add` | plugin manifest `.thclaws-plugin/plugin.json` **or `.claude-plugin/plugin.json`**; `/skill install <git-url>` ; marketplace repo thClaws/marketplace |

## Findings
1. **All 5 converge on SKILL.md + MCP.** Real per-runtime differences are only: frontmatter extras (OpenClaw metadata, Codex openai.yaml), install path, MCP config syntax (JSON `mcpServers` vs TOML vs YAML).
2. thClaws reads Claude Code layout (`.claude/skills`, `.mcp.json`, `.claude-plugin/plugin.json`) -> **one Claude-Code-style plugin dir covers Claude Code + thClaws**.
3. Codex and Hermes need a rendered MCP snippet (TOML / YAML); OpenClaw needs generated `metadata.openclaw` and `{baseDir}` for script paths.
4. NetClaw skills call MCP through a shell wrapper (`mcp-call` + env vars, OpenClaw-specific). To be portable we must rewrite them to call MCP tools natively -> main porting cost.

## Design decisions
- Canonical = Claude-Code plugin layout (`skills/`, `.mcp.json`, `.claude-plugin/`). `build.py` derives: Codex (`openai.yaml` + `config.toml` snippet), Hermes (yaml snippet + skills tree), OpenClaw (inject metadata, strip unsupported keys), thClaws (works as-is; optional `.thclaws-plugin`).
- Skill frontmatter superset: name, description, version, license, risk(read|write), mcp_servers, requires{bins,env}. Generator drops what a runtime ignores.
- Script paths via relative `scripts/`; use `{baseDir}` only in OpenClaw output.

## NetClaw reuse (decision: reuse + extend, Apache-2.0)
- Repo is 198 MB, 243 skills, 53 MCP servers -> do NOT fork wholesale. Use `scripts/import-netclaw.py` to pull selected skills/MCP at a pinned commit, rewrite to our schema, keep LICENSE + per-file header + NOTICE entry listing modifications.
- Candidate first import (read-only, vendor-neutral): subnet calc, pyATS/multivendor-cli, suzieq, batfish, gnmi, syslog, protocol-mcp, nautobot, topology-diagram, rag-mcp.
- Skip: HUD, mobile, Zoom, twitter, tavus/avatar, twilio, worldlabs, tts.
- Security review before import (security-by-design rule): scan every imported skill/MCP (cisco-skill-scanner / vet-third-party-agent-skills), pin dependency versions, strip anything writing to devices unless `risk: write` gate exists.

## Next (P1)
1. Skeleton: skills/, mcp/, adapters/, scripts/build.py, schema + linter.
2. Port 1 skill end-to-end (subnet calc) and prove it loads in Claude Code, Hermes, thClaws (all local/testable), then Codex + OpenClaw.
3. CI: lint + golden render tests.

## Links
- Claude Code plugins: https://code.claude.com/docs/en/plugins-reference
- Codex skills / MCP: https://developers.openai.com/codex/skills , /codex/mcp
- OpenClaw skills: https://docs.openclaw.ai/tools/skills
- thClaws: https://github.com/thClaws/thClaws , https://github.com/thClaws/marketplace
