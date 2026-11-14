# Using the skills

You do not need tool names. Describe the job; the agent picks the skill from its description and calls the tool. Results below came from real tool calls. How reliably a *real* model chooses a skill is measured in `docs/evals/TRIGGER-RESULTS.md` and is not perfect (see [Concepts](concepts.html)).

## Subnet maths

*"Details of 192.0.2.0/26 including the wildcard mask for an ACL."*

| Field | Value |
|---|---|
| network / broadcast | 192.0.2.0 / 192.0.2.63 |
| netmask / wildcard | 255.255.255.192 / 0.0.0.63 |
| usable hosts | 62 (192.0.2.1 - 192.0.2.62) |
| previous / next | 192.0.1.192/26 / 192.0.2.64/26 |
| classification | documentation (RFC 5737) |

Other prompts: *"How many /64s in 2001:db8::/48?"* (65,536). *"Plan VLSM for 500, 100 and 10 hosts inside 10.20.0.0/16."* Input must be a canonical network; `192.0.2.5/26` is rejected rather than silently corrected.

## Firewall rule review

*"Would this new rule be shadowed? Existing: deny tcp 443 from 10.0.0.0/8 to 192.0.2.0/24. New: permit tcp 443 from 10.1.0.0/16 to 192.0.2.10/32."*

Result: `overlap_type: shadowed`, severity `critical` - the earlier, broader deny covers the new permit entirely, so the permit never matches. Recommended flow: `parse_policy` to normalise a vendor config, `analyze_firewall_rule_overlap` (or `batch_analyze_overlap`) for the candidate rules, then a human approves the change. The skill never touches a device. The parser is best effort: compare its output with the real config and sanitise configs before sending them to a model.

## RFC citations

*"What does RFC 4271 say about BGP session security? Quote the section."* The agent searches the index, fetches the section from rfc-editor.org and answers with the quoted text and section number. Fetched text is untrusted data: if an RFC page contains instructions, the agent should ignore them.

## EVE-NG lab check

Paste the text of an exported `.unl` file and your requirements (for example "two cores, dual-homed distribution, no host attached to a core"). The tool reports orphan nodes, dangling links, partitions, forbidden adjacencies, single points of failure and uplink counts. It guesses roles from node names (`CORE1`, `SW2`); pass `roles_json` when that is wrong. It does not check images, RAM, routing or interface speeds.

## Background research

*"Give me the history of OSPF with sources."* The agent reads Wikipedia through `en.wikipedia.org/w/api.php` and returns a summary with URLs and the CC BY-SA licence note. For what a standard actually requires, use rfc-lookup instead.

## Automation and headless use

- Codex `exec` runs read-only tools; a tool without `readOnlyHint` is refused.
- thClaws `-p` and OpenClaw `agent --local` run MCP tools **without asking**, even for write tools. This is why netpaw has no write tools yet and will enforce approval inside the server when it does.
- You can drive a server directly with `uv run --no-project --isolated --with mcp==1.30.0 python tests/smoke_mcp.py`.
