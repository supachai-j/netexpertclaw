---
name: fwrule-analyzer
description: Analyze firewall rules for overlap, shadowing, conflicts and duplicates across PAN-OS, ASA, FTD, IOS/IOS-XE, IOS-XR, Check Point, SRX/Junos, Nokia SR OS and FortiGate, or normalize vendor policies to one schema. Use this skill whenever the user wants to check a new or changed firewall rule against an existing ruleset, audit a policy for redundant, shadowed or never-matching rules, or compare policies across vendors, even if they only paste a rule list or config and never say 'overlap'. Read-only analysis of text you provide; it never contacts or changes a firewall. Not for writing new rules or pushing config.
license: Apache-2.0
compatibility: Requires uv. First start needs network access to fetch hash-locked dependencies (PyPI) and the pinned fwrule-mcp commit (GitHub); the analysis itself makes no network or device calls. Input is text you provide (sanitize customer data first).
metadata:
  version: "1.1.0"
  risk: read
  mcp_servers: "fwrule"
  requires_bins: "uv"
---
<!-- netexpertclaw:imported-from-netclaw -->
# Firewall Rule Analyzer

## MCP Server

- **Server**: `fwrule` (AutomateIP/fwrule-mcp, Apache-2.0), launched by the plugin pinned to a reviewed commit with a pinned requirements file. Do not install it from forks or unpinned sources.
- **Transport**: stdio
- **Requires**: no environment variables; no network or device access (analysis of text/JSON you pass in).

## Available Tools (4)

| Tool | What It Does |
|------|-------------|
| `analyze_firewall_rule_overlap` | Compare a candidate rule against an existing ruleset using 6-dimensional set intersection (zones, addresses, ports, protocols, actions, applications). Detects overlaps, shadowing, conflicts, and duplicates. Supports two input modes: vendor-native config via built-in parsers, or pre-normalized JSON. |
| `parse_policy` | Convert vendor-native firewall configurations into a standardized JSON schema. Enables inspection of parser output — rule counts, object resolution, address expansion — before running overlap analysis. |
| `batch_analyze_overlap` | Analyze several normalized candidate rules against the same normalized ruleset in one call (use `parse_policy` output as `existing_rules`). Pure analysis, normalized-JSON input only. |
| `list_supported_vendors` | Enumerate all supported firewall vendors, their aliases, configuration formats, and explain how to use normalized JSON input to bypass vendor-specific parsers. |

## Supported Vendors (10)

| Vendor | Config Format | Versions | Identifiers |
|--------|---------------|----------|-------------|
| Palo Alto PAN-OS | XML export | 9.x–11.x | `panos`, `paloalto`, `panorama` |
| Cisco ASA | show running-config | 9.x+ | `asa`, `cisco-asa` |
| Cisco FTD | FMC JSON | 6.x–7.x | `ftd`, `firepower`, `fmc` |
| Cisco IOS/IOS-XE | show running-config | 12.x–17.x | `ios`, `iosxe`, `cisco-ios` |
| Cisco IOS-XR | show running-config | 6.x+ | `iosxr`, `ios-xr`, `xr` |
| Check Point | JSON rulebase | R80.x–R82.x | `checkpoint`, `cp`, `check-point` |
| Juniper SRX | display set | 19.x+ | `juniper`, `srx` |
| Juniper Junos | display set | 18.x+ | `junos`, `mx`, `ptx`, `qfx` |
| Nokia SR OS | MD-CLI format | 20.x+ | `sros`, `nokia`, `sr-os` |
| **Fortinet FortiOS** | **Full backup config** | **5.x–7.x** | **`fortios`, `fortigate`, `fortinet`, `forti`, `fgt`, `fmg`** |

## Key Concepts

| Concept | What It Means |
|---------|---------------|
| **Overlap** | Candidate rule matches traffic already handled by existing rules |
| **Shadowing** | Candidate rule is fully covered by a higher-priority existing rule — it will never match |
| **Conflict** | Rules match the same traffic but have different actions (allow vs deny) |
| **Duplication** | Candidate rule is functionally identical to an existing rule |
| **6-Dimensional Analysis** | Comparison across source/dest zones, source/dest addresses, services/ports, protocols, actions, and applications |
| **Normalized JSON** | Vendor-agnostic rule schema with standardized fields (id, position, enabled, action, zones, addresses, services, applications) |

## Two Input Modes

### Mode 1: Vendor-Native Config
Pass raw vendor configuration text and let the built-in parsers normalize it:
- `vendor`: Vendor identifier (e.g., `panos`, `asa`, `ftd`, `ios`, `checkpoint`, `srx`, `junos`, `nokia`, `fortios`)
- `ruleset_payload`: Complete firewall config in vendor format
- `candidate_rule_payload`: Single rule in vendor format
- `os_version`: Optional version hint for parser selection
- `context_objects`: Supplemental object definitions as JSON

### Mode 2: Pre-Normalized JSON
Bypass parsers when structured data is already available:
- `existing_rules`: JSON array of normalized rule objects
- `candidate_rule`: Single normalized JSON rule object

## Workflow: Pre-Change Rule Validation

When adding a new firewall rule to a policy:

1. **Parse existing policy**: `parse_policy` with vendor config — normalize to JSON, verify rule count and object resolution
2. **Analyze candidate**: `analyze_firewall_rule_overlap` — check the proposed rule against the existing ruleset
3. **Review findings**: Examine overlap type (shadow, conflict, duplicate, partial overlap), severity, and affected dimensions
4. **Decision**: Approve, modify, or reject the candidate rule based on findings
5. **Report**: Formatted analysis with vendor, policy, candidate rule, and overlap results

## Workflow: Cross-Vendor Policy Audit

When auditing firewall rules across multiple platforms:

1. **Enumerate vendors**: `list_supported_vendors` — confirm supported platforms
2. **Parse each policy**: `parse_policy` for each vendor config — normalize all rules
3. **Cross-analyze**: For each rule in vendor A, use `analyze_firewall_rule_overlap` against vendor B's normalized rules
4. **Identify**: Cross-platform conflicts, redundant rules, shadowed entries
5. **Report**: Multi-vendor rule consistency analysis

## Workflow: Ruleset Hygiene Audit

When cleaning up an existing firewall policy:

1. **Parse policy**: `parse_policy` — normalize the full ruleset
2. **For each rule**: `analyze_firewall_rule_overlap` — check the rule against all others in the same policy
3. **Flag**: Shadowed rules (dead rules that never match), duplicates, and internal conflicts
4. **Report**: Cleanup recommendations with rule positions and overlap details

## Important Rules

- **Read-only analysis** — all 3 tools are pure analysis; no firewall modifications
- **No credentials required** — works entirely on config text/JSON input, no API connections to firewalls
- **Vendor parsers are best-effort** — use Mode 2 (normalized JSON) when parsers produce unexpected results
- **Data handling** — firewall configs are sensitive. Use lab or sanitized configs; do not paste real customer rulesets, addresses or names into saved artifacts.

## Gotchas

These were observed by running the pinned server (docs/imports/fwrule-analyzer.md):
- Every rule needs a `position`; order decides shadowing. A missing field comes back as a normal tool result with `"success": false` and `error.code: invalid_input` (not an MCP error), so check `success` before reading `overlap_exists`. "No overlap" from a failed call is not a result.
- A later permit that sits under an earlier broader deny is reported as shadowed (never matches); a later broader deny over an earlier permit is reported as `superset` (medium), not as a conflict you can ignore. Quote the `overlap_type` and the rule ids.
- Two identical rules are reported as `exact_duplicate` (severity high).
- Rulesets and configs can hold customer names and addresses (PDPA). Replace them with documentation ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24) before sending them to the tool or saving output.
- (Interpretive, not tested) The tool sees only the policy text you pass. NAT, routing and zones you left out are not considered, so state what was out of scope.
