# netpaw documentation

netpaw packages network-engineering skills for AI agents. A **skill** is a short instruction file (`SKILL.md`, the open [Agent Skills](https://agentskills.io) format) that tells the agent when and how to use a set of **tools**; the tools are small [MCP](https://modelcontextprotocol.io) servers that run locally over stdio. One source tree installs into Claude Code, Codex, Hermes Agent, OpenClaw and thClaws.

## Where to start

1. [Getting started](getting-started.html) - install for your agent in five minutes
2. [Using the skills](using.html) - example prompts and real results
3. [Skill catalog](skills.html) - every tool, input rules, network access, limits
4. [Concepts](concepts.html) - how it fits together, maturity levels, why read-only
5. [Supported agents](agents.html) - what was tested on which agent, and what was not
6. [Safety](safety.html) - threat model, controls, residual risk
7. [Develop](develop.html) - add a skill or an MCP server
8. [Troubleshooting](troubleshoot.html)

Thai pages: [ภาษาไทย](th/index.html) (may lag behind the English pages).

## Status in one table

| Topic | State |
|---|---|
| Skills | 5, all `experimental`, all read-only |
| Agents tested | Claude Code, Hermes Agent (real runtime); Codex, OpenClaw, thClaws (mock model) |
| Real-model results | Claude Code only; other agents are not yet shown to pick the skills with a real LLM |
| Device changes | none; no skill writes to a device |
| Platforms | Ubuntu 24.04 x86_64 only |
| Publishing | GitHub only. Not on PyPI or npm |

Read the status as limits, not as "fully supported". Evidence is in [docs/CONFORMANCE.md](https://github.com/supachai-j/netpaw/blob/main/docs/CONFORMANCE.md) and [docs/READINESS.md](https://github.com/supachai-j/netpaw/blob/main/docs/READINESS.md).

## Data handling

Examples use documentation address ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24, 2001:db8::/32). Do not put real customer names, hostnames, IPs or device configs into prompts, issues or commits. Anything you give an agent may leave your machine through the agent's model provider; sanitise firewall configs first.
