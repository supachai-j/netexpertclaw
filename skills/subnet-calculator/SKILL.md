---
name: subnet-calculator
description: IPv4/IPv6 subnet calculator - CIDR breakdown, usable hosts, wildcard masks for ACLs, previous/next subnets, VLSM planning, same-subnet checks. Use when calculating subnets, sizing a prefix, planning IP addressing, or checking if two IPs share a subnet.
license: Apache-2.0
metadata:
  version: "0.1.0"
  risk: read
  mcp_servers: "subnet-calc"
  requires_bins: "uv"
---

# Subnet Calculator (IPv4 + IPv6)

Read-only. Uses the `subnet-calc` MCP server (tools below). Never contacts devices.
Adapted from NetClaw `subnet-calculator` (Apache-2.0); see NOTICE.

## Tools
- `subnet_calculator(cidr)` - IPv4: network, broadcast, netmask, wildcard, usable hosts, first/last host, previous/next, classification, preview of up to 10 hosts.
- `subnet_calculator_v6(cidr)` - IPv6: range, count of /64s, previous/next, classification, allocation note.
- `subnet_calculator_auto(cidr)` - picks v4/v6.
- `same_subnet(ip_a, ip_b, prefix)` - same-subnet check.

`cidr` must be a canonical network (no host bits, no IPv6 zone). If the tool rejects it, tell the user the corrected network (e.g. `10.1.1.5/24` -> `10.1.1.0/24`) and recompute.

## When to use
Interface addressing, VLSM plans, ACL wildcard masks, route verification, IPv6 site planning, "are these two IPs in the same subnet".

## Procedures
- **Point-to-point**: IPv4 /30 (2 usable) or /31 (RFC 3021); IPv6 /127 (RFC 6164).
- **VLSM**: sort requirements largest-first, pick smallest prefix with enough usable hosts, allocate sequentially from the parent block, verify each with `subnet_calculator`, output a table (name, subnet, prefix, usable, gateway = first host).
- **IPv6 site**: /48 per site, /64 per VLAN; report `count_of_64s`.
- **ACL**: report the wildcard mask exactly as returned.

## Output rules
Give the numbers from the tool, not mental arithmetic. State assumptions (e.g. gateway = first usable host). Do not include customer names or real customer addressing in saved artifacts; use documentation ranges (192.0.2.0/24, 2001:db8::/32) in examples.
