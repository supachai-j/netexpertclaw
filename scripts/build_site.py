#!/usr/bin/env python3
"""Build the static manual site from docs/manual/*.md into site/ . Needs the `markdown` package.
Usage: build_site.py [--out site]"""
import argparse, html, pathlib, re, shutil, sys
import markdown
from common import ROOT

PAGES = [("index", "Overview"), ("getting-started", "Getting started"), ("using", "Using the skills"), ("skills", "Skill catalog"),
         ("concepts", "Concepts"), ("agents", "Supported agents"), ("safety", "Safety"), ("develop", "Develop"),
         ("troubleshoot", "Troubleshooting"), ("roadmap", "Roadmap")]
TH_PAGES = [("index", "ภาพรวม"), ("install", "ติดตั้ง"), ("using", "วิธีใช้"), ("skills", "Skill / Tool"), ("safety", "ความปลอดภัย"),
            ("develop", "พัฒนา"), ("compat", "ความเข้ากันได้"), ("troubleshoot", "แก้ปัญหา")]
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

def render(pages, srcdir, outdir, lang, home_label, other_label, other_href):
    outdir.mkdir(parents=True, exist_ok=True)
    nav_tail = f'<a href="{other_href}" style="margin-top:12px">{html.escape(other_label)}</a>'
    for slug, title in pages:
        src = srcdir / f"{slug}.md"
        body = markdown.markdown(src.read_text(), extensions=["tables", "fenced_code", "sane_lists"])
        nav = "".join(f'<a class="{"on" if s_ == slug else ""}" href="{s_}.html">{html.escape(t)}</a>' for s_, t in pages)
        foot = ("netpaw documentation - source: docs/manual in github.com/supachai-j/netpaw (Apache-2.0). Examples use documentation IP ranges only."
                if lang == "en" else "คู่มือ netpaw - ต้นฉบับ docs/manual ใน github.com/supachai-j/netpaw (Apache-2.0) ตัวอย่างใช้ IP ช่วง documentation เท่านั้น")
        (outdir / f"{slug}.html").write_text(
            f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)} - netpaw</title><link rel="stylesheet" href="{"../" if lang == "th" else ""}style.css"></head>'
            f'<body><div class="wrap"><nav><b>netpaw</b>{nav}{nav_tail}</nav><main>{body}<footer>{html.escape(foot)}</footer></main></div></body></html>')
    return len(pages)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="site"); a = ap.parse_args()
    out = ROOT / a.out
    if out.exists(): shutil.rmtree(out)
    out.mkdir()
    (out / "style.css").write_text(CSS)
    m = ROOT / "docs" / "manual"
    n = render(PAGES, m, out, "en", "Overview", "ภาษาไทย", "th/index.html")
    t = render(TH_PAGES, m / "th", out / "th", "th", "ภาพรวม", "English", "../index.html")
    print("built", n, "English +", t, "Thai pages ->", out)

if __name__ == "__main__":
    sys.exit(main())
