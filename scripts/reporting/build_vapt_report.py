#!/usr/bin/env python3
"""Render Markdown VAPT reports & SOP into branded DEPI PDF (Playwright) and DOCX (python-docx)."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import docx
from docx.shared import Inches, Pt, RGBColor
import markdown
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "docs" / "assets"

CSS = """
@page { size: A4; margin: 17mm 16mm 17mm 16mm; }
* { box-sizing: border-box; }
body { font-family: "Georgia", "Times New Roman", serif; color: #1f2937;
       font-size: 10.2pt; line-height: 1.55; margin: 0; }
.cover { page-break-after: always; padding-top: 4mm; position: relative; min-height: 255mm; }
.band { width: 100%; border-bottom: 2.2pt solid #16273d; padding-bottom: 6mm;
        display: flex; justify-content: space-between; align-items: flex-end; }
.band img.d { height: 21mm; }
.band img.m { height: 13mm; }
.cover-body { padding-top: 28mm; }
.eyebrow { font-family: "Segoe UI", Arial, sans-serif; font-size: 8.8pt;
           letter-spacing: 2.2pt; text-transform: uppercase; color: #0f7b6c; font-weight: 700; }
.title { font-family: "Segoe UI", Arial, sans-serif; font-size: 25pt; line-height: 1.2;
         color: #16273d; font-weight: 700; margin-top: 5mm; }
.sub { font-family: "Segoe UI", Arial, sans-serif; font-size: 11pt; color: #5b6779;
       margin-top: 5mm; line-height: 1.5; }
.short-rule { width: 34mm; height: 2.6pt; background: #0f7b6c; margin: 9mm 0 12mm 0; }
.meta-table { width: 100%; border-collapse: collapse; font-family: "Segoe UI", Arial, sans-serif; font-size: 9.5pt; }
.meta-table td { padding: 2.8mm 3mm; border-bottom: 0.6pt solid #d5dbe3; }
.meta-table td.k { width: 42mm; color: #5b6779; font-weight: 600; text-transform: uppercase; font-size: 8.5pt; }
.cover-foot { position: absolute; bottom: 0; left: 0; right: 0;
              font-family: "Segoe UI", Arial, sans-serif; font-size: 8.4pt; color: #5b6779;
              border-top: 0.8pt solid #d5dbe3; padding-top: 3.5mm;
              display: flex; justify-content: space-between; }
h1 { font-family: "Segoe UI", Arial, sans-serif; color: #16273d; font-size: 16.5pt; font-weight: 700;
     margin: 8mm 0 4mm 0; padding-bottom: 2.5mm; border-bottom: 2pt solid #16273d; page-break-after: avoid; }
h2 { font-family: "Segoe UI", Arial, sans-serif; color: #16273d; font-size: 12.5pt; font-weight: 700;
     margin: 7mm 0 3mm 0; border-left: 3pt solid #0f7b6c; padding-left: 3mm; page-break-after: avoid; }
h3 { font-family: "Segoe UI", Arial, sans-serif; color: #0f7b6c; font-size: 10.8pt; font-weight: 700;
     margin: 5mm 0 2mm 0; page-break-after: avoid; }
p { margin: 2.2mm 0; text-align: left; }
ul, ol { margin: 2.2mm 0; padding-left: 6mm; }
li { margin: 1mm 0; }
table { width: 100%; border-collapse: collapse; margin: 4mm 0; font-size: 8.8pt;
        font-family: "Segoe UI", Arial, sans-serif; }
th { background: #16273d; color: #fff; padding: 2.2mm 2.5mm; text-align: left; font-size: 8.3pt; }
td { padding: 2mm 2.5mm; border-bottom: 0.6pt solid #d5dbe3; vertical-align: top; word-break: break-word; }
tr { page-break-inside: avoid; }
tr:nth-child(even) td { background: #f6f8fa; }
code { font-family: Consolas, "Courier New", monospace; font-size: 8.4pt;
       background: #f7f8fa; padding: .3mm 1.1mm; color: #0b4f45; }
pre { background: #f7f8fa; border: 0.6pt solid #d5dbe3; border-left: 2.6pt solid #0f7b6c;
      padding: 3mm 3.8mm; margin: 3.2mm 0; white-space: pre-wrap; overflow-wrap: break-word; }
pre code { background: none; padding: 0; color: #1a2b32; font-size: 8.1pt; line-height: 1.42; }
blockquote { margin: 3.2mm 0; padding: 2.8mm 4mm; background: #f3f7f6;
             border-left: 2.6pt solid #0f7b6c; color: #14453d; page-break-inside: avoid; }
img.poc { max-width: 100%; border: 0.8pt solid #d5dbe3; margin: 3mm 0 5mm 0; display: block; page-break-inside: avoid; }
"""


def resolve_images_in_html(html: str, md_dir: Path) -> str:
    def _repl(match: re.Match) -> str:
        alt = match.group(1)
        src = match.group(2)
        p = Path(src)
        if not p.is_absolute():
            p = (md_dir / src).resolve()
        if p.exists():
            return f'<img class="poc" src="{p.as_uri()}" alt="{alt}"/>'
        return match.group(0)

    return re.sub(r'<img alt="([^"]*)" src="([^"]+)"\s*/?>', _repl, html)


def build_pdf(md_path: Path, pdf_out: Path, title: str, subtitle: str, doc_type: str) -> None:
    md_text = md_path.read_text(encoding="utf-8")
    body_html = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists", "smarty"],
        output_format="html5",
    )
    body_html = resolve_images_in_html(body_html, md_path.parent)
    assets_uri = ASSETS.as_uri()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>{title}</title><style>{CSS}</style></head>
<body>
<div class="cover">
  <div class="band">
    <img class="d" src="{assets_uri}/logo-depi.png" alt="DEPI"/>
    <img class="m" src="{assets_uri}/logo-mcit.png" alt="MCIT"/>
  </div>
  <div class="cover-body">
    <div class="eyebrow">DEPI Graduation Program &nbsp;&middot;&nbsp; Project 5</div>
    <div class="title">{title}</div>
    <div class="sub">{subtitle}</div>
    <div class="short-rule"></div>
    <table class="meta-table">
      <tr><td class="k">Document Type</td><td>{doc_type}</td></tr>
      <tr><td class="k">Author / Analyst</td><td>Mohamed Reda Elhaddad (@7adadd)</td></tr>
      <tr><td class="k">Date</td><td>2026-11-26</td></tr>
      <tr><td class="k">AI Runtime</td><td>Local Ollama (llama3.2:3b + qwen2.5:3b) &mdash; Zero Cloud APIs</td></tr>
      <tr><td class="k">Scope</td><td>Isolated Self-Owned Lab (AD Dataset, DVWA, DIVA APK)</td></tr>
    </table>
  </div>
  <div class="cover-foot">
    <span>AI-Assisted VAPT Automation &amp; Reporting Workflow</span>
    <span>github.com/7adadd/AI-Assisted-VAPT-Automation-Reporting-Workflow</span>
  </div>
</div>
<main>{body_html}</main>
</body></html>"""

    html_tmp = ROOT / "reports" / "_build" / f"{pdf_out.stem}.html"
    html_tmp.parent.mkdir(parents=True, exist_ok=True)
    html_tmp.write_text(html, encoding="utf-8")

    pdf_out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_tmp.as_uri(), wait_until="networkidle")
        page.pdf(
            path=str(pdf_out),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=(
                '<div style="width:100%;font-size:8px;color:#5b6779;font-family:Segoe UI,Arial;'
                'padding:0 16mm;display:flex;justify-content:space-between;">'
                f'<span>{title}</span>'
                '<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>'
                '</div>'
            ),
            margin={"top": "17mm", "bottom": "17mm", "left": "16mm", "right": "16mm"},
        )
        browser.close()
    print(f"OK PDF -> {pdf_out}")


def build_docx(md_path: Path, docx_out: Path, title: str, subtitle: str) -> None:
    doc = docx.Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    h = doc.add_heading(title, level=0)
    h.runs[0].font.color.rgb = RGBColor(0x16, 0x27, 0x3D)
    p = doc.add_paragraph(subtitle)
    p.add_run("\nAuthor: Mohamed Reda Elhaddad (@7adadd) | Date: 2026-11-26 | Scope: Isolated Lab Only")
    doc.add_page_break()

    lines = md_path.read_text(encoding="utf-8").splitlines()
    in_code = False
    code_buf = []
    table_buf = []

    def flush_table():
        nonlocal table_buf
        if not table_buf:
            return
        rows = [
            [c.strip() for c in r.strip().strip("|").split("|")]
            for r in table_buf
            if not re.match(r"^\s*\|?[\s:\-\|]+\|?\s*$", r)
        ]
        if rows:
            cols = max(len(r) for r in rows)
            tbl = doc.add_table(rows=len(rows), cols=cols)
            tbl.style = "Table Grid"
            for r_i, row in enumerate(rows):
                for c_i, val in enumerate(row):
                    if c_i < cols:
                        cell = tbl.cell(r_i, c_i)
                        cell.text = val
                        if r_i == 0 and cell.paragraphs[0].runs:
                            cell.paragraphs[0].runs[0].bold = True
        table_buf = []

    for line in lines:
        if line.strip().startswith("```"):
            flush_table()
            if in_code:
                cp = doc.add_paragraph("\n".join(code_buf))
                for run in cp.runs:
                    run.font.name = "Consolas"
                    run.font.size = Pt(8.5)
                code_buf = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue

        if line.strip().startswith("|") and "|" in line.strip()[1:]:
            table_buf.append(line)
            continue
        flush_table()

        img_m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line.strip())
        if img_m:
            img_p = (md_path.parent / img_m.group(2)).resolve()
            if img_p.exists():
                doc.add_picture(str(img_p), width=Inches(5.8))
                cap = doc.add_paragraph(img_m.group(1))
                cap.italic = True
            continue

        if line.startswith("# "):
            hd = doc.add_heading(line[2:].strip(), level=1)
            if hd.runs:
                hd.runs[0].font.color.rgb = RGBColor(0x16, 0x27, 0x3D)
        elif line.startswith("## "):
            hd = doc.add_heading(line[3:].strip(), level=2)
            if hd.runs:
                hd.runs[0].font.color.rgb = RGBColor(0x0F, 0x7B, 0x6C)
        elif line.startswith("### "):
            doc.add_heading(line[4:].strip(), level=3)
        elif line.startswith("- ") or line.startswith("* "):
            doc.add_paragraph(line[2:].strip(), style="List Bullet")
        elif re.match(r"^\d+\.\s+", line):
            doc.add_paragraph(re.sub(r"^\d+\.\s+", "", line), style="List Number")
        elif line.strip():
            doc.add_paragraph(line.strip())

    flush_table()
    docx_out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(docx_out))
    print(f"OK DOCX -> {docx_out}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build branded PDF and DOCX from Markdown VAPT report/SOP.")
    ap.add_argument("input_md")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--docx")
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--doc-type", default="VAPT Technical Deliverable")
    args = ap.parse_args()

    md_p = Path(args.input_md)
    build_pdf(md_p, Path(args.pdf), args.title, args.subtitle, args.doc_type)
    if args.docx:
        build_docx(md_p, Path(args.docx), args.title, args.subtitle)
    return 0


if __name__ == "__main__":
    sys.exit(main())
