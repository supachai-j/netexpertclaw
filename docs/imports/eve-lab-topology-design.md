# eve-lab-topology-design - upstream review and plan (NOT yet built)
Upstream: NetClaw `workspace/skills/eve-lab-topology-design` @cfafa46c (Apache-2.0): 37-line SKILL.md, 3 reference docs, `scripts/validate_unl_topology.py` (608 lines, stdlib only: argparse, json, xml.etree, pathlib).
Read on 2026-11-14 (grep + read of the skill, not of the whole validator):
- VERIFIED: the design skill itself needs no credentials and no network; the validator imports only the stdlib and opens only files named on its command line.
- VERIFIED: its sibling skills `eve-lab-topology-discovery/-build/-validation` call the `eve-ng-mcp-server` (live EVE-NG with EVE_URL/EVE_USER/EVE_PASSWORD; build includes `eve_create_network`/`eve_delete_network`). These are NOT part of this import.
- VERIFIED: our lint forbids scripts inside skill folders, so the validator cannot ship as a bundled script.
- INTERPRETIVE: parsing a user-supplied .unl with `xml.etree` accepts DTD/entity expansion unless guarded (same class as the fwrule PAN-OS parser); needs a DOCTYPE rejection, size cap, and node/link count caps.
- NOT CHECKED: the validator's correctness on real .unl files, its role-prefix heuristics, the three reference docs line by line.
Plan (D-10): import the design workflow skill; expose the validator as a read-only MCP tool `validate_unl_topology(unl_text, requirements_json?)` in a new server `eve-lab` (stdlib, offline, no egress, no file path argument, so no filesystem reads). Guards: reject DOCTYPE/ENTITY, 2 MB cap, 500 nodes / 2000 links, `additionalProperties:false`. Tests with synthetic .unl fixtures (documentation addresses only), including a billion-laughs and an external-entity sample. Evals: 10+10 trigger queries, 2 output evals. Maturity: experimental. Cross-review by the tester role; security review by the security role when enabled (parser).
Out of scope: anything that talks to EVE-NG, creates/deletes labs, or opens consoles (needs a server-side write gate first).
