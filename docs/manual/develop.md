# Develop

## Layout

```
skills/<name>/SKILL.md      source skill (agent-neutral), evals/ with trigger and output cases
mcp/servers.json            server registry ({root} = install path); egress and capability per server
mcp/<server>/               our server code, or launcher + hash-locked requirements for an upstream one
mcp/_shared/                shared helpers (strict input, hidden-character stripper)
profiles.json               minimal | standard | online | full
imports/netclaw.json        pinned imports from NetClaw
scripts/                    build, lint, import, eval and cache tools
tests/                      unit, security regression, smoke MCP, runtime scripts
docs/                       plan, decisions (ADR style), reviews, conformance, manual
```

## Skill frontmatter

```yaml
---
name: my-skill            # equals the folder name, lowercase and dashes, max 64
description: "Use this skill when ... because ..."   # when to use, what it does; no ': ' or ' #' in plain scalars
license: Apache-2.0
compatibility: Requires uv. Network egress to example.org only.
metadata:
  version: "0.1.0"
  risk: read              # read | write
  maturity: experimental  # experimental | tested | recommended
  mcp_servers: "my-server"
  requires_bins: "uv"
---
```

Only `name, description, license, compatibility, metadata` are allowed at top level; no `allowed-tools`. Files next to `SKILL.md` are limited to `references/*.md`, `agents/*.yaml` and `evals/*.json`. Write tool names plainly, without agent prefixes. A `risk: write` skill needs `metadata.approval: required` and an `## Approval` section, but the real gate must be in the server.

## Add an MCP server

1. Prefer stdlib Python. Use FastMCP only for the wrapper; call `harden` so unknown fields are rejected. Read tools: `ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)`. Write tools must not set `readOnlyHint`.
2. Register it in `mcp/servers.json` with `capability`, an explicit `egress` list (`[]` if none) and `uv run --quiet --no-project --isolated --with mcp==<pin> python {root}/mcp/<name>/server.py`.
3. Generate the tool-definition lock: `python3 scripts/gen_tools_cache.py <name>`.
4. Add tests, including hostile input (oversize, malformed, hidden characters, injection text in fetched data).

## Dev loop

```bash
bin/netpaw lint && bin/netpaw test && bin/netpaw smoke
NETPAW_LIVE_TESTS=1 python3 -m unittest discover -s tests   # also live checks against public hosts
python3 scripts/gen_tools_cache.py --all --check             # tool definitions unchanged
claude plugin validate .
```

Security tools used in CI: gitleaks, bandit, semgrep, pip-audit, zizmor, `skills-ref`. Run them locally with the pinned versions in `.github/workflows/security.yml`.

## Evaluate a skill

- Trigger evaluation: `python3 scripts/eval_triggers.py --runs 3 --out <file> <skill>` (uses Claude Code and your model quota; tell reviewers how many calls you made).
- Output evaluation: `scripts/eval_outputs.py` compares answers with and without the skill using deterministic checks.
- Record what was run and the output in `docs/evals/`. Do not write a number you did not measure.

## Import a skill from NetClaw

```bash
python3 scripts/import-netclaw.py --upstream <checkout at the pinned commit>
```

The script verifies the commit, takes only `SKILL.md`, applies exact-match edits (fails if upstream changed), rewrites frontmatter, records hashes and updates `NOTICE`. Every import also needs a review note in `docs/imports/<skill>.md` (what upstream does, what we changed, what we did not check) and a licence check. The order of work is in `docs/imports/NETCLAW-PLAN.md`.

## Reporting a runtime test

State the agent and version, OS, exact commands, whether the model was real or mock, level reached (L1-L4) and raw output. Say what you did not test. Clean up test installs afterwards.

## Process

Roles, gates and the rule that an author must not be the only security reviewer: `docs/AI-SDLC.md`. Decisions are numbered in `docs/DECISIONS.md`. Contribution rules: `CONTRIBUTING.md`.
