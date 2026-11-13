# netexpertclaw — Plan v0.1

## 1. Goal
One canonical set of network-engineer skills (audit, troubleshoot, change-with-approval) + MCP servers, packaged automatically for 5 runtimes: Claude Code, Codex, Hermes Agent, OpenClaw, thclaw.

## 2. What NetClaw does (ideas to keep / drop)
Keep: SKILL.md per workflow, MCP servers for device/tool access, safety model (read-only default, baseline -> change -> verify, approval gate for writes, audit trail), SKILL-SCHEMA with `mcp_servers` dependency list.
Drop (for now): HUD, mobile app, Zoom, VS Code ext, federation (N2N). NetClaw is a full product; we ship portable skills + thin installer.
Pain we fix: NetClaw is OpenClaw/Hermes-centric, skills use OpenClaw-specific `metadata.openclaw` and `mcp-call` shell wrapper. We make runtime-neutral.

## 3. Architecture
```
skills/<name>/SKILL.md      # canonical, runtime-neutral (name, description, version, license, mcp_servers, risk: read|write)
mcp/<server>/               # MCP servers (stdio), or pointers to upstream (pyATS, etc.)
adapters/
  claude-code/   -> .claude-plugin/plugin.json + skills/ (+ .mcp.json)   (marketplace-installable)
  codex/         -> AGENTS.md + ~/.codex/config.toml [mcp_servers] snippet (+ skills dir if supported)
  hermes/        -> ~/.hermes/skills/<cat>/<name>/ + mcp_servers config
  openclaw/      -> workspace/skills/<name> with metadata.openclaw block generated
  thclaw/        -> TBD after format research
scripts/build.py  # renders adapters/ from skills/ ; `install.sh --runtime X`
tests/            # lint frontmatter, render-per-runtime golden tests, MCP smoke tests vs. lab
lab/              # containerlab / FRR testbed for CI
```
Principle: write skill once; generator emits per-runtime frontmatter/paths/MCP config. Skills call MCP tools natively (no shell wrapper).

## 4. Safety (non-negotiable, from security-by-design rule / NetClaw)
- Read-only by default; write skills declare `risk: write` and require explicit human approval + pre/post baseline.
- Credentials via env/secret manager only, never in repo/skills. `.env.example` only.
- Command allow/deny lists in MCP layer; output redaction (IPs/secrets optional) before returning to the LLM.
- Audit log (JSONL) of every tool call. Treat device output as untrusted (prompt-injection).
- Lab-first: all write skills must pass against a lab testbed before release.

## 5. Phases
P0 (1 wk) Research: confirm formats for each runtime — Claude Code plugin/skills spec, Codex skills/AGENTS.md + MCP config, Hermes skills + mcp, OpenClaw skill metadata, **thclaw (need link/repo — unknown to me)**. Output: docs/RUNTIME-MATRIX.md.
P1 (1-2 wk) Core: skill schema, build.py, adapters for Claude Code + Hermes (what we run daily), lint + CI.
P2 (2 wk) First 5 skills + MCP: network-inventory, device-health-audit (read), config-backup/diff, ospf/bgp-troubleshoot, subnet-calc. MCP via pyATS/Netmiko/NAPALM/gNMI; lab testbed in CI.
P3 (1-2 wk) Adapters: Codex, OpenClaw, thclaw. Cross-runtime conformance test (same prompt -> same tool calls on lab).
P4 Write-change workflow (baseline -> approval -> push -> verify -> rollback), audit log, redaction.
P5 Thai-language docs, vendor packs (Cisco/Fortinet/Palo Alto/F5…), RAG over runbooks, release v0.1.

## 6. Open questions
1. thClaws: https://thclaws.ai (resolved, see RUNTIME-MATRIX)
2. GitHub account: supachai-j (confirmed).
3. Initial vendor focus (Cisco IOS-XE? FortiGate? multi-vendor)?
4. Reuse NetClaw code: DECIDED — reuse + extend (Apache-2.0, attribution kept). See RUNTIME-MATRIX.
5. Customer data: never in repo (PDPA); lab/synthetic only.
