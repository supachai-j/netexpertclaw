# netpaw

**Network-engineering skills for any AI agent.** Subnet maths, firewall-rule analysis, RFC lookup and lab-topology checks, written once as open-standard [Agent Skills](https://agentskills.io) plus [MCP](https://modelcontextprotocol.io) tools, and installed into Claude Code, Codex, Hermes Agent, OpenClaw and thClaws from a single source.

[![ci](https://github.com/supachai-j/netpaw/actions/workflows/ci.yml/badge.svg)](https://github.com/supachai-j/netpaw/actions/workflows/ci.yml)
[![security](https://github.com/supachai-j/netpaw/actions/workflows/security.yml/badge.svg)](https://github.com/supachai-j/netpaw/actions/workflows/security.yml)
License: Apache-2.0 · Status: **pre-release, every skill is `experimental`** (what that means: [docs/READINESS.md](docs/READINESS.md))

[Documentation](https://supachai-j.github.io/netpaw-docs/) · [Thai / ภาษาไทย](README.th.md) · [Contributing](CONTRIBUTING.md) · [Security policy](SECURITY.md)

## Why

Network engineers keep re-explaining the same things to AI assistants and keep getting confident wrong answers: a wildcard mask off by one bit, an RFC quoted from memory, a firewall rule that "should work" but is shadowed by an older one. netpaw gives the agent **deterministic tools** for those jobs and **short skills** that tell it when to use them, so the answer is computed or quoted from a source, not recalled.

Design goals:
- **Write once, run on many agents.** A skill is a plain `SKILL.md` (open spec); its tools are MCP servers over stdio. `netpaw install` puts them where each agent looks.
- **Read-only first.** No skill changes a device today. Anything that could will need an approval gate enforced inside its MCP server, not just text in a prompt ([why](docs/manual/safety.md)).
- **Small, auditable and pinned.** Each server is stdlib Python (or a hash-pinned upstream), declares exactly which hosts it may contact, and has its tool definitions hash-locked in CI.
- **Honest about maturity.** Skills carry an evidence-based level; we say what was tested and what was not.

## What is in it

| Skill | What it does | Network |
|---|---|---|
| `subnet-calculator` | IPv4/IPv6 subnet details, wildcard masks, VLSM planning, same-subnet check | none |
| `fwrule-analyzer` | Finds shadowed, overlapping, conflicting and duplicate firewall rules across vendors (PAN-OS, ASA/FTD, IOS/XE/XR, Check Point, SRX, FortiGate, Nokia SR OS; see `list_supported_vendors`) | none |
| `rfc-lookup` | Search the RFC index, fetch an RFC or a single section, with citation | `www.rfc-editor.org` only |
| `eve-lab-topology-design` | Design an EVE-NG lab and validate exported `.unl` text: orphan nodes, dangling links, partitions, forbidden adjacencies, single points of failure | none |
| `wikipedia-research` | Background and history of a protocol or technology, with sources and licence | `en.wikipedia.org` only |

Details, tool names and limits: [docs/manual/skills.md](docs/manual/skills.md).

## Quick start

Requirements: Python 3 (tested with 3.12), [`uv`](https://docs.astral.sh/uv/), git. Tested on Ubuntu 24.04 (x86_64) only.

```bash
git clone https://github.com/supachai-j/netpaw.git && cd netpaw
bin/netpaw doctor                  # checks uv, python and which agents are present
bin/netpaw list                    # skills, risk level, maturity, network egress
bin/netpaw install -a codex -p standard --root "$PWD"            # dry run: shows what would change
bin/netpaw install -a codex -p standard --root "$PWD" --with-mcp --apply
```

`netpaw install` is a **dry run unless you pass `--apply`**, backs up any config it edits, and `netpaw uninstall --apply` removes only what it installed. Profiles: `minimal`, `standard`, `online` (adds the two skills that use the internet), `full`.

Claude Code (plugin, from a clone): `claude --plugin-dir ./netpaw`. The marketplace route (`/plugin marketplace add supachai-j/netpaw`) has not been tested yet.

Then ask your agent something like: *"Are 192.0.2.10 and 192.0.2.70 in the same /26?"* (it should call `same_subnet` and answer no). More examples: [docs/manual/using.md](docs/manual/using.md).

> There is **no `pip install netpaw` or `npx netpaw`**: this project is not published to PyPI or npm. Install from this repository only.

## Supported agents

| Agent | Tested version | Level reached |
|---|---|---|
| Claude Code | 2.1.322 | skill visible, MCP connected, real model called the tools |
| Hermes Agent | v0.23.1 | skill visible, MCP connected (no model-driven call test) |
| Codex CLI | 0.169.0 | all four levels with a mock model; cold start may hide tools for the first turns |
| OpenClaw | 2026.11.3 | all four levels with a mock model; tools are reached through `tool_search` |
| thClaws | 0.156.0 | all four levels with a mock model |

"Mock model" proves the path agent → MCP server → result, not that a real LLM picks the right skill. The full method and evidence: [docs/CONFORMANCE.md](docs/CONFORMANCE.md). Other agents that read the open `SKILL.md` layout (`.agents/skills`, opencode, Cursor, Gemini CLI) are targeted by the installer but **not tested**; PRs with test evidence are welcome.

## Safety model in one paragraph

All tools are read-only and say so (`readOnlyHint`); none needs credentials; each server can only reach the hosts it declares (`egress`) and the CI fails if code imports network modules without declaring one. Text fetched from the internet is labelled untrusted and stripped of control and hidden characters. Dependencies are pinned with hashes, GitHub Actions are pinned by commit, and every release carries an SBOM and build provenance. Independent reviews and their findings are in [docs/SECURITY-REVIEW.md](docs/SECURITY-REVIEW.md); report vulnerabilities as described in [SECURITY.md](SECURITY.md). A clean scan or review is evidence, not a guarantee.

## Maturity

`experimental` (all five today) → `tested` → `recommended`, each with required evidence (runtime tests, trigger evaluation, injection cases, output evaluation versus no skill). See [docs/READINESS.md](docs/READINESS.md) and measured numbers in [docs/evals/TRIGGER-RESULTS.md](docs/evals/TRIGGER-RESULTS.md). Known weak spot: a model often answers simple subnet questions from memory without calling the tool.

## Roadmap

Next: server-side approval gate for write tools, multi-host egress policy, then more read-only skills chosen from the 242 in [NetClaw](https://github.com/automateyournetwork/netclaw) by risk (see [docs/ROADMAP.md](docs/ROADMAP.md) and [docs/imports/NETCLAW-PLAN.md](docs/imports/NETCLAW-PLAN.md)). Deliberately **not** imported: tools that open listening ports, accept arbitrary CLI, or write device config without a gate.

## Contributing

Issues and PRs are welcome: new skills, runtime test reports, parser fuzzing, doc fixes. Read [CONTRIBUTING.md](CONTRIBUTING.md) first (documentation IP ranges only, no customer data, claims need evidence, DCO sign-off).

## Credits and licence

Apache-2.0. Inspired by and partly derived from [NetClaw](https://github.com/automateyournetwork/netclaw) (Apache-2.0) and uses [fwrule-mcp](https://github.com/AutomateIP/fwrule-mcp) at a pinned commit; see [NOTICE](NOTICE). The `SKILL.md` layout follows the [Agent Skills specification](https://agentskills.io). Project history: [docs/HISTORY.md](docs/HISTORY.md).
