# Concepts

## Skill, tool, server

- A **skill** (`skills/<name>/SKILL.md`) is Markdown with a small YAML header. The header's `description` is what the agent reads to decide whether to use it; the body says how. It follows the open Agent Skills spec and is checked in CI with the official `skills-ref` validator.
- A **tool** is a function the agent can call (for example `same_subnet`).
- An **MCP server** (`mcp/<name>/`) is a local process that offers tools over stdio. `mcp/servers.json` is the single registry; `scripts/build.py` turns it into each agent's config format.

A skill without its server is only advice; a server without its skill works but the agent may not know when to use it. netpaw ships them as a pair.

## One source, many agents

`skills/` and `mcp/servers.json` are agent-neutral. `bin/netpaw install` (or `scripts/build.py`) copies skills to each agent's skill directory and writes or merges MCP config in that agent's format (TOML, YAML, JSON, CLI). Tool names are written plainly in `SKILL.md`; each agent adds its own prefix.

## Why read-only first

Models can be steered by text they read (RFC pages, Wikipedia, device output, configs). A read-only tool turns "the model was fooled" into "the model said something wrong", which a human can catch. A write tool turns it into a change on a device. Two measurements shaped the design: headless thClaws (`-p`) and OpenClaw (`--local`) run MCP tools without asking, and the MCP spec says clients must not trust tool annotations. So approval for any future write tool must be enforced inside its server (baseline, approval bound to device and payload, verify, audit), not by the agent or a prompt.

## Maturity levels

| Level | Evidence required |
|---|---|
| `experimental` | lint, unit and smoke tests and CI security jobs pass; `risk: read`; official validator passes; scanned (Cisco Skill Scanner, SkillSpector) with a working control; independent security review for any skill with network egress |
| `tested` | experimental + installs and works on every agent we claim + trigger evaluation run 3x per query, validation pass at least 80% with no false positives + at least one prompt-injection case passes |
| `recommended` | tested + output evaluation beats the no-skill baseline on hard cases + tried on realistic synthetic data without serious errors |

No skill is above `experimental` yet. `netpaw list` shows the level. Numbers and method: `docs/READINESS.md`, `docs/evals/TRIGGER-RESULTS.md`.

## Trigger evaluation

For each skill there are 20 labelled queries (should / should not trigger, split into train and validation). `scripts/eval_triggers.py` runs them through Claude Code with the plugin loaded and counts whether the skill's tool was called. One run per query is noisy (about plus/minus 2 queries), so read results as ranges.

## Egress declaration

Each server lists the hosts it may contact in `mcp/servers.json` (`egress`). Lint fails when a server imports network modules but declares none, and `netpaw list` shows egress next to every skill so you can see what leaves your machine.
