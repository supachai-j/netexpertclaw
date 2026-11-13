"""Shared helpers: minimal frontmatter parser (stdlib only), skill discovery."""
from __future__ import annotations
import json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
REQUIRED = ("name", "description", "license")
META_REQUIRED = ("version", "risk")
RISKS = ("read", "write")


def split(text: str):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise ValueError("missing frontmatter")
    return m.group(1), m.group(2)


def parse_fm(fm: str) -> dict:
    out, cur = {}, None
    for line in fm.splitlines():
        if not line.strip():
            continue
        if line.startswith("  "):
            k, _, v = line.strip().partition(":")
            out[cur][k.strip()] = v.strip().strip('"')
        else:
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if v == "":
                out[k] = {}; cur = k
            else:
                out[k] = v.strip('"')
    return out


def load_skill(d: pathlib.Path) -> dict:
    text = (d / "SKILL.md").read_text()
    fm, body = split(text)
    meta = parse_fm(fm)
    return {"dir": d, "meta": meta, "fm": fm, "body": body, "text": text}


def skills():
    return [load_skill(p.parent) for p in sorted((ROOT / "skills").glob("*/SKILL.md"))]


def servers() -> dict:
    return json.loads((ROOT / "mcp" / "servers.json").read_text())
