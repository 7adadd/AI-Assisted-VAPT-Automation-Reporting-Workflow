#!/usr/bin/env python3
"""Build the branded DEPI documentation HTML/PDF for the VAPT workflow project.

Subcommands:
  build                Convert all markdown docs -> docs HTML (TOC page numbers from toc_pages.json if present)
  toc <pass1.pdf>      Scan a rendered PDF for section start pages, rewrite TOC, re-emit HTML
  png <pdf> <outdir>   Render every PDF page to PNG for visual review

Output: reports/_build/docs.html  (+ toc_pages.json, PNGs)
"""
import json
import sys
from pathlib import Path

import markdown
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "reports" / "_build"
ASSETS = ROOT / "docs" / "assets"

SECTIONS = [
    ("overview", ROOT / "README.md", "1", "Project Overview", "Purpose, repository structure, quickstart"),
    ("plan", ROOT / "docs" / "00-PROJECT-PLAN.md", "2", "Master Project Plan", "Four-week day-by-day schedule and twelve-day fast track"),
    ("lab", ROOT / "docs" / "01-LAB-SETUP-GUIDE.md", "3", "AI Lab Setup Guide", "WSL low-disk lab, runtimes, models, targets"),
    ("prompts", ROOT / "docs" / "02-PROMPT-LIBRARY.md", "4", "Prompt Library", "Template standard and twenty-three starter prompts"),
    ("ethics", ROOT / "docs" / "03-PRIVACY-ETHICS-CHECKLIST.md", "5", "Privacy and Ethics Checklist", "Mandatory gate before any testing"),
    ("validation", ROOT / "docs" / "04-VALIDATION-FRAMEWORK.md", "6", "Validation Framework", "Anti-hallucination procedure and accuracy metrics"),
]

# --- Restrained, print-oriented palette (no gradients, no pills) -------------
NAVY = "#16273d"
ACCENT = "#0f7b6c"
INK = "#1f2937"
GRAY = "#5b6779"
RULE = "#d5dbe3"
ZEBRA = "#f6f8fa"
CODEBG = "#f7f8fa"

CSS = """
@page { size: A4; margin: 17mm 16mm 17mm 16mm; }
* { box-sizing: border-box; }
body { font-family: "Georgia", "Times New Roman", serif; color: %(INK)s;
       font-size: 10.3pt; line-height: 1.55; margin: 0; }

/* ============ COVER ============ */
.cover { page-break-after: always; padding-top: 4mm; }
.band { width: 100%%; border-bottom: 2.2pt solid %(NAVY)s; padding-bottom: 6mm;
        display: flex; justify-content: space-between; align-items: flex-end; }
.band img.d { height: 21mm; }
.band img.m { height: 13mm; }
.cover-body { padding-top: 30mm; }
.eyebrow { font-family: "Segoe UI", Arial, sans-serif; font-size: 8.6pt;
           letter-spacing: 2.4pt; text-transform: uppercase; color: %(ACCENT)s; font-weight: 700; }
.title { font-family: "Segoe UI", Arial, sans-serif; font-size: 27pt; line-height: 1.2;
         color: %(NAVY)s; font-weight: 700; margin-top: 5mm; letter-spacing: -0.4pt; }
.sub { font-family: "Segoe UI", Arial, sans-serif; font-size: 11pt; color: %(GRAY)s;
       margin-top: 5mm; line-height: 1.5; }
.short-rule { width: 34mm; height: 2.6pt; background: %(ACCENT)s; margin: 9mm 0 0 0; }

.prepared { margin-top: 16mm; }
.prepared h3 { font-family: "Segoe UI", Arial, sans-serif; font-size: 8.6pt; letter-spacing: 2pt;
               text-transform: uppercase; color: %(NAVY)s; margin: 0 0 4mm 0; font-weight: 700; }
.group-line { font-family: "Segoe UI", Arial, sans-serif; font-size: 10pt; color: %(INK)s;
              padding-bottom: 2mm; border-bottom: 0.8pt solid %(RULE)s; margin-bottom: 6mm; }
.group-line span.k { color: %(GRAY)s; font-size: 8.8pt; letter-spacing: 1pt;
                     text-transform: uppercase; margin-right: 4mm; }
table.members { width: 100%%; border-collapse: collapse; font-family: "Segoe UI", Arial, sans-serif;
                font-size: 9.4pt; }
table.members td { padding: 2.5mm 3mm; border-bottom: 0.6pt solid %(RULE)s; color: %(INK)s; }
table.members td.n { width: 8mm; color: %(ACCENT)s; font-weight: 700; }
table.members td.name { color: %(GRAY)s; }

.cover-foot { position: absolute; bottom: 0; left: 0; right: 0;
              font-family: "Segoe UI", Arial, sans-serif; font-size: 8.4pt; color: %(GRAY)s;
              border-top: 0.8pt solid %(RULE)s; padding-top: 3.5mm;
              display: flex; justify-content: space-between; }

/* ============ CONTENTS ============ */
.toc { }
.toc h1 { font-family: "Segoe UI", Arial, sans-serif; color: %(NAVY)s; font-size: 19pt;
          margin: 0 0 2mm 0; font-weight: 700; }
.toc .lead { font-family: "Segoe UI", Arial, sans-serif; font-size: 9pt; color: %(GRAY)s;
             border-bottom: 2.2pt solid %(NAVY)s; padding-bottom: 4mm; }
table.toc { width: 100%%; border-collapse: collapse; margin-top: 4mm;
            font-family: "Segoe UI", Arial, sans-serif; }
table.toc td { padding: 3.1mm 2mm; border-bottom: 0.6pt solid %(RULE)s; vertical-align: baseline; }
table.toc td.n { width: 12mm; color: %(ACCENT)s; font-size: 11pt; font-weight: 700; }
table.toc td.t { font-size: 10.8pt; color: %(NAVY)s; font-weight: 600; }
table.toc td.p { width: 14mm; text-align: right; font-size: 10.8pt; color: %(NAVY)s; font-weight: 700; }

.control { margin-top: 10mm; }
.control h3 { font-family: "Segoe UI", Arial, sans-serif; font-size: 8.8pt; letter-spacing: 1.6pt;
              text-transform: uppercase; color: %(NAVY)s; font-weight: 700; margin: 0 0 3mm 0; }
dl.control-l { margin: 0; font-family: "Segoe UI", Arial, sans-serif; font-size: 8.9pt; }
dl.control-l .row { display: flex; border-bottom: 0.6pt solid %(RULE)s; }
dl.control-l dt { flex: 0 0 34mm; color: %(GRAY)s; padding: 1.9mm 0; }
dl.control-l dd { flex: 1 1 auto; margin: 0; padding: 1.9mm 0; color: %(INK)s; }

/* ============ CONTENT ============ */
section.doc { page-break-before: always; }
h1 { font-family: "Segoe UI", Arial, sans-serif; color: %(NAVY)s; font-size: 17pt; font-weight: 700;
     margin: 0 0 6mm 0; padding-bottom: 3mm; border-bottom: 2.2pt solid %(NAVY)s; letter-spacing: -0.2pt;
     page-break-after: avoid; }
h1 .secno { color: %(ACCENT)s; margin-right: 3mm; }
h2 { font-family: "Segoe UI", Arial, sans-serif; color: %(NAVY)s; font-size: 12.4pt; font-weight: 700;
     margin: 8mm 0 3mm 0; page-break-after: avoid; }
h3 { font-family: "Segoe UI", Arial, sans-serif; color: %(INK)s; font-size: 10.8pt; font-weight: 700;
     margin: 6mm 0 2mm 0; page-break-after: avoid; }
p { margin: 2.4mm 0; text-align: justify; orphans: 3; widows: 3; }
ul, ol { margin: 2.4mm 0; padding-left: 6mm; }
li { margin: 1.2mm 0; page-break-inside: avoid; }

table { width: 100%%; border-collapse: collapse; margin: 4mm 0; font-size: 9.2pt;
        font-family: "Segoe UI", Arial, sans-serif; page-break-inside: auto; }
th { background: %(NAVY)s; color: #fff; padding: 2.4mm 3mm; text-align: left;
     font-size: 8.5pt; font-weight: 600; letter-spacing: .3pt; }
td { padding: 2.2mm 3mm; border-bottom: 0.6pt solid %(RULE)s; vertical-align: top; }
tr { page-break-inside: avoid; }
tr:nth-child(even) td { background: %(ZEBRA)s; }

code { font-family: Consolas, "Courier New", monospace; font-size: 8.7pt;
       background: %(CODEBG)s; padding: .3mm 1.2mm; color: #0b4f45; }
pre { background: %(CODEBG)s; border: 0.6pt solid %(RULE)s; border-left: 2.6pt solid %(ACCENT)s;
      padding: 3.2mm 4mm; margin: 3.5mm 0;
      page-break-inside: auto; white-space: pre-wrap; overflow-wrap: break-word; }
pre code { background: none; padding: 0; color: #1a2b32; font-size: 8.3pt;
           line-height: 1.45; white-space: pre-wrap; overflow-wrap: break-word; }

blockquote { margin: 3.5mm 0; padding: 3mm 4.5mm; background: #f3f7f6;
             border-left: 2.6pt solid %(ACCENT)s; color: #14453d; page-break-inside: avoid; }
blockquote p { margin: 1mm 0; text-align: left; }
blockquote p { margin: 1mm 0; text-align: left; }
hr { border: none; border-top: 0.8pt solid %(RULE)s; margin: 6mm 0; }
a { color: %(ACCENT)s; text-decoration: none; }
strong { color: %(NAVY)s; }
img { max-width: 100%%; }
""" % {"NAVY": NAVY, "ACCENT": ACCENT, "INK": INK, "GRAY": GRAY,
       "RULE": RULE, "ZEBRA": ZEBRA, "CODEBG": CODEBG}

MEMBERS = [
    ("1", "Mohamed Reda Elhaddad (@7adadd) — Lead & Sole Executor"),
]


def md_to_html(md_text: str) -> str:
    return markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists", "smarty"],
        output_format="html5",
    )


def build_html() -> None:
    toc_pages = {}
    toc_file = BUILD / "toc_pages.json"
    if toc_file.exists():
        toc_pages = json.loads(toc_file.read_text(encoding="utf-8"))

    assets_uri = ASSETS.as_uri()
    sections_html, toc_rows = [], []
    for key, path, num, title, desc in SECTIONS:
        body = md_to_html(path.read_text(encoding="utf-8"))
        sections_html.append(
            f'<section class="doc" id="sec-{key}"><h1><span class="secno">{num}</span>{title}</h1>{body}</section>'
        )
        toc_rows.append(
            f'<tr><td class="n">{num}</td><td class="t">{title}</td>'
            f'<td class="p">{toc_pages.get(key, "&ndash;")}</td></tr>'
        )

    member_rows = "\n".join(
        f'<tr><td class="n">{n}</td><td class="name">{label}</td></tr>' for n, label in MEMBERS
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>AI-Assisted VAPT Automation and Reporting Workflow — Documentation</title>
<style>{CSS}</style></head>
<body>

<div class="cover">
  <div class="band">
    <img class="d" src="{assets_uri}/logo-depi.png" alt="DEPI"/>
    <img class="m" src="{assets_uri}/logo-mcit.png" alt="MCIT"/>
  </div>

  <div class="cover-body">
    <div class="eyebrow">DEPI Graduation Program &nbsp;&middot;&nbsp; Project 5</div>
    <div class="title">AI-Assisted VAPT Automation<br/>&amp; Reporting Workflow</div>
    <div class="sub">A privacy-first, human-in-the-loop penetration testing workflow
      powered by locally-hosted language models.</div>
    <div class="short-rule"></div>

    <div class="prepared">
      <h3>Prepared By</h3>
      <div class="group-line"><span class="k">Track</span>DEPI Graduation Program — Cyber Security (Solo Delivery)</div>
      <table class="members">
{member_rows}
      </table>
    </div>
  </div>

  <div class="cover-foot">
    <span>Version 1.0 &nbsp;&middot;&nbsp; November 2026</span>
    <span>github.com/7adadd/AI-Assisted-VAPT-Automation-Reporting-Workflow</span>
  </div>
</div>

<div class="toc">
  <h1>Contents</h1>
  <div class="lead">AI-Assisted VAPT Automation and Reporting Workflow &mdash; project documentation</div>
  <table class="toc">{''.join(toc_rows)}</table>

  <div class="control">
    <h3>Document Control</h3>
    <dl class="control-l">
      <div class="row"><dt>Project</dt><dd>AI-Assisted VAPT Automation and Reporting Workflow (DEPI Project 5)</dd></div>
      <div class="row"><dt>Owner</dt><dd>@7adadd</dd></div>
      <div class="row"><dt>Status</dt><dd>Active &mdash; Week 1 execution</dd></div>
      <div class="row"><dt>Review cycle</dt><dd>Updated at each weekly checkpoint</dd></div>
      <div class="row"><dt>Classification</dt><dd>Educational &mdash; self-owned lab environment only</dd></div>
    </dl>
  </div>
</div>

{''.join(sections_html)}
</body></html>"""

    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "docs.html").write_text(html, encoding="utf-8")
    print(f"OK html -> {BUILD / 'docs.html'}")


def cmd_toc(pdf_path: str) -> None:
    doc = pymupdf.open(pdf_path)
    anchors = {
        "overview": "1 Project Overview",
        "plan": "2 Master Project Plan",
        "lab": "3 AI Lab Setup Guide",
        "prompts": "4 Prompt Library",
        "ethics": "5 Privacy and Ethics Checklist",
        "validation": "6 Validation Framework",
    }
    found = {}
    # Skip cover (p1) and the contents page (p2) — section headings live after them.
    for pno in range(2, doc.page_count):
        text = doc[pno].get_text("text").replace("\n", "")
        for key, needle in anchors.items():
            if key not in found and needle in text:
                found[key] = pno + 1
    missing = [k for k in anchors if k not in found]
    if missing:
        raise SystemExit(f"TOC detection failed for: {missing}")
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "toc_pages.json").write_text(json.dumps(found, indent=2), encoding="utf-8")
    print("OK toc ->", found)


def cmd_png(pdf_path: str, outdir: str) -> None:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    for pno in range(doc.page_count):
        pix = doc[pno].get_pixmap(dpi=110)
        pix.save(out / f"page-{pno + 1:02d}.png")
    print(f"OK {doc.page_count} pages -> {out}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "build":
        build_html()
    elif cmd == "toc" and len(sys.argv) == 3:
        cmd_toc(sys.argv[2])
        build_html()
    elif cmd == "png" and len(sys.argv) == 4:
        cmd_png(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        sys.exit(1)