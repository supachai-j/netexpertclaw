---
name: subnet-calculator
description: Calculate and verify IPv4/IPv6 subnets - CIDR breakdown, usable hosts, ACL wildcard masks, previous/next subnets, VLSM and addressing plans, and same-subnet checks. Use this skill whenever the user sizes a prefix, splits a block between sites or VLANs, writes a wildcard or network statement, checks whether two addresses share a subnet, or asks about /30, /31, /48 or /64 style masks, even if they never say "subnet". Exact numbers come from the tool, not mental arithmetic. Use it even for questions that look easy (same-subnet, host counts, masks), because mental subnet arithmetic is error-prone, so do not answer from memory. Not for DNS, DHCP or live device queries.
license: Apache-2.0
compatibility: Requires uv (Python is fetched by uv). Offline, no network access and no device access.
metadata:
  version: "0.1.0"
  risk: read
  maturity: experimental
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

## Gotchas
Verified against the server:
- Host bits are rejected, not rounded: `192.0.2.5/24` errors with "has host bits set". Tell the user the canonical network (`192.0.2.0/24`) and recompute; do not report numbers for the host address.
- Only `address/prefix` is accepted. `192.0.2.0/255.255.255.0` and IPv6 zones (`fe80::1%eth0/64`) are rejected; convert the mask yourself first.
- `/31` reports 2 usable hosts (RFC 3021 point-to-point) and `/32` reports 1. Do not "correct" them to 0 or subtract network/broadcast.
- 192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24 and 2001:db8::/32 are classified `documentation`, not `private`; 100.64.0.0/10 is `shared address space / CGNAT`. Use the classification the tool returns.
- A wildcard mask is the inverse of the netmask (`/26` -> `0.0.0.63`); give the tool's value, not a recalculation.
