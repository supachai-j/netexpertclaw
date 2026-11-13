#!/usr/bin/env python3
"""Build the static manual site from docs/manual/*.md into site/ . Needs the `markdown` package.
Usage: build_site.py [--out site]"""
import argparse, html, pathlib, re, shutil, sys
import markdown
from common import ROOT

PAGES = [("index", "ภาพรวม"), ("install", "ติดตั้ง"), ("using", "วิธีใช้"), ("skills", "Skill / Tool"),
         ("safety", "ความปลอดภัย"), ("develop", "พัฒนา"), ("compat", "ความเข้ากันได้"), ("troubleshoot", "แก้ปัญหา")]
CSS = """
:root{--bg:#0f1419;--fg:#e6edf3;--mut:#8b98a5;--acc:#4fc3f7;--card:#161d26;--bd:#2a3441;--warn:#f0b429}
@media(prefers-color-scheme:light){:root{--bg:#fff;--fg:#1c2733;--mut:#5b6b7b;--acc:#0b6bcb;--card:#f4f7fa;--bd:#d6dde4;--warn:#9a6700}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.7 system-ui,"Noto Sans Thai","Sarabun",sans-serif}
.wrap{display:flex;min-height:100vh}nav{width:240px;padding:24px 16px;border-right:1px solid var(--bd);position:sticky;top:0;height:100vh;flex:none}
nav b{display:block;margin-bottom:14px;font-size:18px}nav a{display:block;padding:7px 10px;border-radius:6px;color:var(--mut);text-decoration:none}
nav a.on,nav a:hover{background:var(--card);color:var(--acc)}main{max-width:900px;padding:32px 40px 80px;flex:1;min-width:0}
h1{font-size:30px;margin-top:0}h2{margin-top:36px;border-bottom:1px solid var(--bd);padding-bottom:6px}a{color:var(--acc)}
code{background:var(--card);padding:2px 6px;border-radius:4px;font-size:.92em}pre{background:var(--card);border:1px solid var(--bd);padding:14px;border-radius:8px;overflow:auto}
pre code{background:none;padding:0}table{border-collapse:collapse;width:100%;display:block;overflow:auto;margin:16px 0}
th,td{border:1px solid var(--bd);padding:8px 10px;text-align:left;vertical-align:top}th{background:var(--card)}
blockquote{margin:16px 0;padding:10px 16px;border-left:4px solid var(--warn);background:var(--card);color:var(--fg)}
footer{margin-top:60px;color:var(--mut);font-size:13px}
@media(max-width:800px){.wrap{display:block}nav{width:auto;height:auto;position:static;border-right:0;border-bottom:1px solid var(--bd);display:flex;flex-wrap:wrap;gap:4px}nav b{width:100%}main{padding:20px}}
"""

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="site"); a = ap.parse_args()
    out = ROOT / a.out
    if out.exists(): shutil.rmtree(out)
    out.mkdir()
    (out / "style.css").write_text(CSS)
    for slug, title in PAGES:
        src = ROOT / "docs" / "manual" / f"{slug}.md"
        body = markdown.markdown(src.read_text(), extensions=["tables", "fenced_code", "sane_lists"])
        body = re.sub(r'href="([a-z]+)\.html"', r'href="\1.html"', body)
        nav = "".join(f'<a class="{"on" if s == slug else ""}" href="{s}.html">{html.escape(t)}</a>' for s, t in PAGES)
        (out / f"{slug}.html").write_text(
            f'<!doctype html><html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="robots" content="noindex"><title>{html.escape(title)} · NetExpertClaw</title><link rel="stylesheet" href="style.css"></head>'
            f'<body><div class="wrap"><nav><b>NetExpertClaw</b>{nav}</nav><main>{body}<footer>NetExpertClaw manual · เนื้อหาจาก docs/manual ใน repo (private) · ตัวอย่างใช้ IP ช่วง documentation</footer></main></div></body></html>')
    print("built", len(PAGES), "pages ->", out)

if __name__ == "__main__":
    sys.exit(main())
