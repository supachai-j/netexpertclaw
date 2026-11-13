"""Pure-stdlib subnet maths (no network, no device access). Read-only."""
from __future__ import annotations
import ipaddress


_DOC = [ipaddress.ip_network(x) for x in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "2001:db8::/32")]


def _classify(net) -> str:
    if any(net.version == d.version and net.subnet_of(d) for d in _DOC): return "documentation (RFC 5737/3849)"
    if net.is_loopback: return "loopback"
    if net.is_link_local: return "link-local"
    if net.is_multicast: return "multicast"
    if net.is_private: return "private/ULA" if net.version == 6 else "private"
    if net.is_reserved: return "reserved"
    return "global"


def _parse(cidr: str, version: int):
    if not isinstance(cidr, str) or "/" not in cidr or len(cidr) > 64:
        raise ValueError("cidr must look like 10.0.0.0/24")
    if "%" in cidr:
        raise ValueError("IPv6 zones are not supported")
    net = ipaddress.ip_network(cidr.strip(), strict=True)  # host bits -> ValueError
    if net.version != version:
        raise ValueError(f"expected IPv{version} CIDR")
    return net


def subnet_v4(cidr: str) -> dict:
    n = _parse(cidr, 4)
    total = n.num_addresses
    if n.prefixlen >= 31:
        first, last, usable = n.network_address, n.broadcast_address, total
    else:
        first, last, usable = n.network_address + 1, n.broadcast_address - 1, total - 2
    out = {
        "network": str(n.network_address), "broadcast": str(n.broadcast_address),
        "prefix": n.prefixlen, "netmask": str(n.netmask), "wildcard": str(n.hostmask),
        "host_bits": 32 - n.prefixlen, "total_addresses": str(total), "usable_hosts": str(usable),
        "first_host": str(first), "last_host": str(last),
        "classification": _classify(n),
        "previous": None, "next": None,
    }
    size = total
    base = int(n.network_address)
    if base - size >= 0:
        out["previous"] = f"{ipaddress.IPv4Address(base - size)}/{n.prefixlen}"
    if base + size <= 2**32 - 1:
        out["next"] = f"{ipaddress.IPv4Address(base + size)}/{n.prefixlen}"
    out["hosts_preview"] = [str(h) for _, h in zip(range(10), n.hosts() if n.prefixlen < 31 else iter(n))]
    return out


def subnet_v6(cidr: str) -> dict:
    n = _parse(cidr, 6)
    total = n.num_addresses
    notes = {128: "single host", 127: "point-to-point (RFC 6164)", 64: "standard LAN, SLAAC capable",
             56: "small site", 48: "site allocation", 32: "ISP/LIR allocation"}
    base = int(n.network_address)
    out = {
        "network": str(n.network_address), "exploded": n.network_address.exploded,
        "last": str(n.broadcast_address), "prefix": n.prefixlen, "host_bits": 128 - n.prefixlen,
        "total_addresses": str(total),
        "count_of_64s": str(2 ** (64 - n.prefixlen)) if n.prefixlen <= 64 else "0 (smaller than /64)",
        "classification": _classify(n), "note": notes.get(n.prefixlen),
        "previous": f"{ipaddress.IPv6Address(base - total)}/{n.prefixlen}" if base - total >= 0 else None,
        "next": f"{ipaddress.IPv6Address(base + total)}/{n.prefixlen}" if base + total <= 2**128 - 1 else None,
    }
    return out


def subnet_auto(cidr: str) -> dict:
    return (subnet_v6 if ":" in cidr else subnet_v4)(cidr)


def same_subnet(ip_a: str, ip_b: str, prefix: int) -> dict:
    a, b = ipaddress.ip_address(ip_a), ipaddress.ip_address(ip_b)
    if a.version != b.version:
        raise ValueError("address families differ")
    na = ipaddress.ip_network(f"{a}/{prefix}", strict=False)
    nb = ipaddress.ip_network(f"{b}/{prefix}", strict=False)
    return {"same_subnet": na == nb, "subnet_a": str(na), "subnet_b": str(nb)}
