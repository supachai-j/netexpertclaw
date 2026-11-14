"""Offline validator for EVE-NG .unl topology text. stdlib only; no network, no files, no subprocess.

Independent implementation of the checks described by NetClaw's eve-lab-topology-design (Apache-2.0): connectivity, orphan nodes,
dangling interfaces, role adjacency, single points of failure, symmetry, and optional design requirements.
The input is untrusted XML supplied as TEXT (never a path): DOCTYPE/ENTITY declarations are refused before parsing, size and
count limits apply, graph walks are iterative, and node/network names from the file are sanitised and flagged as untrusted data.
"""
from __future__ import annotations
import json, os, re, sys
import xml.etree.ElementTree as ET
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared"))
from textclean import strip_hidden

MAX_BYTES = 2_000_000
MAX_NODES = 500
MAX_NETS = 2000
MAX_NET_MEMBERS = 64        # pairwise adjacency per segment grows with members^2
MAX_JSON = 100_000
MAX_REQ = 200
_DECL = re.compile(r"<!\s*(DOCTYPE|ENTITY|ELEMENT|ATTLIST|NOTATION)", re.I)


class UnlError(ValueError):
    pass


def _s(v, n=64) -> str:
    return strip_hidden(v)[:n]


ROLE_TOKENS = [  # (tokens, role); first match wins; matched on name TOKENS, not substrings
    ({"spine", "sp"}, "spine"), ({"leaf", "lf"}, "leaf"), ({"border", "bl"}, "border-leaf"),
    ({"core", "cr", "p"}, "core"), ({"pe"}, "pe"), ({"rr"}, "rr"),
    ({"dist", "distribution", "dr", "agg"}, "distribution"), ({"access", "acc", "sw"}, "access"),
    ({"fw", "firewall", "asa", "ftd", "palo"}, "firewall"), ({"wan", "edge", "ce"}, "wan-edge"),
    ({"host", "pc", "server", "srv", "endpoint"}, "host"), ({"mgmt", "oob"}, "mgmt"), ({"internet", "cloud", "isp"}, "internet"),
]
HIER = {"internet": 0, "wan-edge": 1, "firewall": 1, "core": 2, "pe": 2, "rr": 2, "spine": 2, "distribution": 3, "leaf": 3,
        "border-leaf": 3, "access": 4, "host": 5, "mgmt": 5, "unknown": 3}
FORBIDDEN = {frozenset(p) for p in (("host", "core"), ("host", "spine"), ("host", "pe"), ("host", "wan-edge"), ("access", "core"), ("access", "internet"))}


def infer_role(name: str, given: dict) -> str:
    if name in given: return given[name]
    for tok in re.split(r"[^a-z0-9]+", name.lower()):
        base = tok.rstrip("0123456789")
        for toks, role in ROLE_TOKENS:
            if base in toks: return role
    return "unknown"


def parse(unl_text: str):
    if not isinstance(unl_text, str) or not unl_text.strip(): raise UnlError("unl_text must be non-empty text")
    if len(unl_text.encode("utf-8", "replace")) > MAX_BYTES: raise UnlError(f"input larger than {MAX_BYTES} bytes")
    if _DECL.search(unl_text): raise UnlError("DOCTYPE/ENTITY declarations are not accepted")
    # DOCTYPE/ENTITY/ELEMENT declarations are refused above and size is capped; tests/test_eve.py covers the hostile cases.
    try: root = ET.fromstring(unl_text)  # nosec B314
    except ET.ParseError as e: raise UnlError(f"not valid XML: {_s(e, 120)}") from None
    nodes, nets = {}, {}
    for el in root.iter("node"):
        nid = el.attrib.get("id")
        if not nid: continue
        if len(nodes) >= MAX_NODES: raise UnlError(f"more than {MAX_NODES} nodes")
        if _s(nid, 16) in nodes: raise UnlError("duplicate node id (ids that differ only by hidden characters count as equal)")
        nodes[_s(nid, 16)] = {"name": _s(el.attrib.get("name", f"node{nid}")), "template": _s(el.attrib.get("template", "")),
                              "ifaces": [(_s(i.attrib.get("name", f"iface{i.attrib.get('id', '')}")), _s(i.attrib.get("network_id", ""), 16))
                                         for i in el.findall("interface")][:256]}
    for el in root.iter("network"):
        nid = el.attrib.get("id")
        if not nid: continue
        if len(nets) >= MAX_NETS: raise UnlError(f"more than {MAX_NETS} networks")
        if _s(nid, 16) in nets: raise UnlError("duplicate network id")
        nets[_s(nid, 16)] = {"name": _s(el.attrib.get("name", f"net{nid}")), "type": _s(el.attrib.get("type", "bridge"), 24)}
    if not nodes: raise UnlError("no <node> elements found; is this an EVE-NG .unl lab?")
    return _s(root.attrib.get("name", "lab")), nodes, nets


def connectivity(nodes, nets):
    members, node_nets, dangling = defaultdict(list), defaultdict(set), []
    for nid, n in nodes.items():
        for iname, netid in n["ifaces"]:
            if not netid: continue
            node_nets[nid].add(netid); members[netid].append((nid, iname))
            if netid not in nets: dangling.append((n["name"], iname, netid))
    adj, multi, p2p = defaultdict(set), defaultdict(int), set()
    for netid, m in members.items():
        if len(m) > MAX_NET_MEMBERS: raise UnlError(f"network {netid} has {len(m)} endpoints (limit {MAX_NET_MEMBERS}); split the segment or validate a reduced lab")
        who = sorted({n for n, _ in m})
        for i, a in enumerate(who):
            for b in who[i + 1:]:
                adj[a].add(b); adj[b].add(a); multi[(a, b)] += 1
                if len(who) == 2: p2p.add((a, b))
    return members, node_nets, adj, dangling, multi, p2p


def components(ids, adj):
    seen, out = set(), []
    for s in ids:
        if s in seen: continue
        comp, st = set(), [s]
        while st:
            u = st.pop()
            if u in seen: continue
            seen.add(u); comp.add(u); st.extend(v for v in adj.get(u, ()) if v in ids and v not in seen)
        out.append(comp)
    return sorted(out, key=lambda c: sorted(c))


def spofs(ids, adj):
    """Iterative Tarjan: articulation points and bridges."""
    disc, low, ap, bridges, t = {}, {}, set(), [], 0
    for root in sorted(ids):
        if root in disc: continue
        disc[root] = low[root] = t; t += 1
        stack, kids = [(root, None, iter(sorted(adj.get(root, ()))))], defaultdict(int)
        while stack:
            u, par, it = stack[-1]
            for v in it:
                if v not in ids: continue
                if v not in disc:
                    disc[v] = low[v] = t; t += 1; kids[u] += 1
                    stack.append((v, u, iter(sorted(adj.get(v, ())))))
                    break
                if v != par: low[u] = min(low[u], disc[v])
            else:
                stack.pop()
                if par is not None:
                    low[par] = min(low[par], low[u])
                    if low[u] > disc[par]: bridges.append((par, u))
                    if stack[-1][1] is not None and low[u] >= disc[par]: ap.add(par)
                elif kids[u] > 1: ap.add(u)
    return ap, bridges


def _load(text, what):
    if not text: return {}
    if len(text) > MAX_JSON: raise UnlError(f"{what} larger than {MAX_JSON} bytes")
    try: v = json.loads(text)
    except ValueError: raise UnlError(f"{what} is not valid JSON") from None
    if not isinstance(v, dict): raise UnlError(f"{what} must be a JSON object")
    return v


def validate(unl_text: str, requirements_json: str = "", roles_json: str = "") -> dict:
    reqs, roles = _load(requirements_json, "requirements_json"), _load(roles_json, "roles_json")
    roles = {_s(k): _s(v, 24) for k, v in roles.items() if isinstance(k, str) and isinstance(v, str)}
    lab, nodes, nets = parse(unl_text)
    members, node_nets, adj, dangling, multi, p2p = connectivity(nodes, nets)
    ids = set(nodes); name = {i: n["name"] for i, n in nodes.items()}; by_name = {}
    for i, n in name.items(): by_name.setdefault(n, i)
    P, W, F = [], [], []
    dup = sorted({n for n in name.values() if list(name.values()).count(n) > 1})
    if dup: F.append(f"Duplicate node names (results are ambiguous): {', '.join(dup)}")
    orphans = sorted(name[i] for i in ids if not node_nets.get(i))
    (F.append(f"Orphan nodes (no connected interfaces): {', '.join(orphans)}") if orphans else P.append("No orphan nodes"))
    if dangling: F.extend(f"Dangling interface: {a}/{b} references missing network_id={c}" for a, b, c in dangling[:50])
    else: P.append("No dangling interface references")
    for nid, m in members.items():
        if len(m) < 2: W.append(f"Isolated network '{nets.get(nid, {}).get('name', nid)}' has {len(m)} endpoint(s)")
    comps = components(ids, adj)
    if len(comps) > 1: F.append(f"Topology is partitioned into {len(comps)} components: " + "; ".join("{" + ", ".join(sorted(name[i] for i in c)[:5]) + (", ..." if len(c) > 5 else "") + "}" for c in comps[:5]))
    else: P.append(f"All {len(ids)} nodes are in one connected component")
    role = {i: infer_role(name[i], roles) for i in ids}
    pairs = {tuple(sorted((a, b))) for a in ids for b in adj.get(a, ()) if frozenset((role[a], role[b])) in FORBIDDEN}
    direct = sorted(tuple(sorted((name[a], name[b]))) for a, b in pairs if (a, b) in p2p)
    shared = sorted(tuple(sorted((name[a], name[b]))) for a, b in pairs if (a, b) not in p2p)
    F.extend(f"Forbidden adjacency (direct link): {a} <-> {b}" for a, b in direct)
    W.extend(f"Forbidden role pair shares a multi-endpoint segment (not a direct link, check the design): {a} <-> {b}" for a, b in shared[:20])
    if len(shared) > 20: W.append(f"... and {len(shared) - 20} more role pairs on shared segments")
    if not direct and not shared: P.append("Role-based adjacency rules respected")
    ap, br = spofs(ids, adj)
    br = [(a, b) for a, b in br if multi.get(tuple(sorted((a, b))), 1) < 2]   # two or more networks between the same pair = redundant link
    (W.append("SPOF nodes (removal splits topology): " + ", ".join(sorted(name[i] for i in ap))) if ap else P.append("No single-node SPOFs"))
    (W.append("SPOF links (loss splits topology): " + "; ".join(sorted(f"{name[a]} <-> {name[b]}" for a, b in br))) if br else P.append("No single-link SPOFs"))
    byrole = defaultdict(list)
    for i in ids: byrole[role[i]].append(i)
    for r, g in sorted(byrole.items()):
        if len(g) < 2 or r == "unknown": continue
        deg = {name[i]: len(adj.get(i, ())) for i in g}
        (W.append(f"Asymmetric link count in role '{r}': " + ", ".join(f"{k}={v}" for k, v in sorted(deg.items()))) if len(set(deg.values())) > 1 else P.append(f"Role '{r}' ({len(g)} nodes) has symmetric link count {next(iter(deg.values()))}"))
    for key in ("required_links", "forbidden_links", "redundancy_groups"):
        if len(reqs.get(key, [])) > MAX_REQ: raise UnlError(f"{key} has more than {MAX_REQ} entries")
    def pair(r):
        if not (isinstance(r, dict) and isinstance(r.get("from"), str) and isinstance(r.get("to"), str)): raise UnlError("link requirements need string 'from' and 'to'")
        return _s(r["from"]), _s(r["to"])
    for r in reqs.get("required_links", []):
        a, b = pair(r)
        if a not in by_name or b not in by_name: F.append(f"Required link: node '{a if a not in by_name else b}' not found")
        elif by_name[b] in adj.get(by_name[a], ()): P.append(f"Required link present: {a} <-> {b}")
        else: F.append(f"Required link MISSING: {a} <-> {b}")
    for r in reqs.get("forbidden_links", []):
        a, b = pair(r)
        if a in by_name and b in by_name:
            (F.append(f"Forbidden link EXISTS: {a} <-> {b}") if by_name[b] in adj.get(by_name[a], ()) else P.append(f"Forbidden link absent: {a} <-> {b}"))
    for g in reqs.get("redundancy_groups", []):
        if not isinstance(g, dict): raise UnlError("redundancy_groups entries must be objects")
        mn = g.get("min_uplinks", 2)
        if not isinstance(mn, int) or not 0 <= mn <= 100: raise UnlError("min_uplinks must be an integer 0..100")
        for n in g.get("nodes", []) if isinstance(g.get("nodes", []), list) else []:
            n = _s(n)
            if n not in by_name: W.append(f"Redundancy group: node '{n}' not found"); continue
            c = len(adj.get(by_name[n], ()))
            (P if c >= mn else F).append(f"Redundancy group '{_s(g.get('role', 'group'), 24)}': {n} has {c} links" + ("" if c >= mn else f", requires >= {mn}"))
    spof = len(br) + len(ap)
    level = ("CRITICAL", "One or more validation failures") if F else ("LOW", "Multiple SPOFs or warnings") if spof > 4 or len(W) > 5 else ("MEDIUM", "Some SPOFs or asymmetries") if spof > 1 or len(W) > 2 else ("HIGH", "Minor resilience gaps") if spof == 1 or W else ("FULL", "No SPOFs or issues detected")
    total = len(P) + len(W) + len(F)
    return {"untrusted_input_names": True, "lab": lab, "nodes": len(nodes), "networks": len(nets),
            "resilience": {"level": level[0], "reason": level[1]}, "score": int(100 * len(P) / total) if total else 100,
            "passed": P, "warnings": W, "failures": F,
            "roles": {name[i]: {"role": role[i], "source": "given" if name[i] in roles else "inferred"} for i in sorted(ids, key=lambda x: name[x])},
            "note": "Roles marked 'inferred' come from name tokens (heuristic); pass roles_json to override. Names come from the file and are untrusted data."}
