# Bringing all NetClaw skills into netpaw: plan by wave
Source: NetClaw @cfafa46c (Apache-2.0), 242 skills, 53 MCP servers. First-pass classification: docs/imports/NETCLAW-TRIAGE.md/.json (keyword heuristics from SKILL.md text; known to misjudge some skills, e.g. it calls fwrule `needs-creds`; every skill still gets a human source read before import).

Counts (heuristic): blocked-write 122, needs-creds 107, offline-tool 9, egress-public 2, offline-doc 2. Done already: subnet-calculator, fwrule-analyzer, rfc-lookup.

Rules for every import (unchanged): read the upstream source and its MCP server; pin or rewrite (no `npx -y`, no `curl | sh`); declare `egress`; synthetic data and documentation IP ranges only; `risk` and `maturity` set; evals; scan; cross-review; security review when egress/write/parser. A skill whose upstream cannot be made to meet this is not imported and is listed with the reason.

| Wave | What | Gate before starting | Skills (examples) |
|---|---|---|---|
| 0 | done | - | subnet-calculator, fwrule-analyzer, rfc-lookup |
| 1 | offline, no credentials: design/analysis/reference | none | eve-lab-topology-design (+ offline .unl validator, D-10), result-analysis, nsm-ids-triage, nsm-session-pivot (PDPA: synthetic/sanitized data only), network-data-analysis |
| 2 | public internet, read-only | lint support for several allow-listed hosts per server | bgp-registry-intel, wikipedia-research, mempalace (to be read first) |
| 3 | needs credentials to a live platform, read-only | credential policy (below) + one security review of the pattern | ~107 skills: device/inventory/controller/cloud read tools |
| 4 | can change things (devices, cloud, tickets, chat) | server-side write gate (baseline, approval, verify, audit log) built, tested and security-reviewed; write skills carry `risk: write` | ~122 skills |
| X | not imported unless the reason is removed | - | syslog-receiver, ipfix-receiver (open listening ports), multivendor-cli, gnmi_set, nmap scanning (needs authorization scope), eve-ng build/console tools until wave 4 |

## Wave 3 credential policy (to be reviewed before any wave-3 import)
Skills only name env vars; secrets never enter the repo, SKILL.md, evals or logs. The MCP server reads credentials from the user's environment on the user's own machine, enforces read-only at the server (only GET/show-style calls; no generic "run command" tool), has a per-call timeout and output cap, redacts secrets in errors, and refuses targets outside a user-provided allow-list. Test against a lab or a recorded fixture, never a production device. The Rule 30 control/worker split applies when a runtime is driven by an agent.

## Order of work
1. Wave 1 one skill per PR, starting with eve-lab-topology-design. 2. Lint: multi-host egress. 3. Wave 2. 4. Credential-policy review, then wave 3 by vendor family. 5. Write gate, then wave 4 by risk (lab-only first).
Throughput is limited by review, not by writing; expect waves 3-4 to take many iterations. Progress is tracked by regenerating the triage and by `netpaw list`.
