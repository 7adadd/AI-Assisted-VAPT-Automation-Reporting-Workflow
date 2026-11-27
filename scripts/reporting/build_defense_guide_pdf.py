#!/usr/bin/env python3
"""Render deliverables/PROJECT-WALKTHROUGH-AND-DEFENSE-GUIDE.md to a clean Arabic RTL/LTR branded PDF."""
from __future__ import annotations

import html as html_lib
import re
import sys
from pathlib import Path

import markdown
import pymupdf
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "docs" / "assets"
BUILD = ROOT / "reports" / "_build"
MD_IN = ROOT / "deliverables" / "PROJECT-WALKTHROUGH-AND-DEFENSE-GUIDE.md"
PDF_OUT = ROOT / "deliverables" / "PROJECT-WALKTHROUGH-AND-DEFENSE-GUIDE.pdf"

CSS = """
@page {
  size: A4;
  margin: 16mm 15mm 18mm 15mm;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  direction: rtl;
  font-family: "Segoe UI", "Tahoma", "Arial", sans-serif;
  color: #172536;
  font-size: 10.2pt;
  line-height: 1.72;
}

/* Cover */
.cover {
  page-break-after: always;
  min-height: 256mm;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 6mm 4mm 4mm;
}
.cover-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 2.2pt solid #0c1a2c;
  padding-bottom: 6mm;
  direction: ltr;
}
.logos-left { display: flex; align-items: center; gap: 12px; }
.cover-top img.depi { height: 20mm; }
.cover-top img.aegis { height: 18mm; border-radius: 4mm; }
.cover-top img.mcit { height: 13mm; }

.cover-hero {
  margin-top: 24mm;
  text-align: right;
}
.eyebrow {
  display: inline-block;
  font-size: 9.5pt;
  font-weight: 700;
  color: #0a7367;
  background: #e6f6f4;
  border: 1px solid #99e2d8;
  padding: 2mm 4.5mm;
  border-radius: 999px;
}
.cover-title {
  font-size: 25pt;
  font-weight: 800;
  color: #0c1a2c;
  margin: 7mm 0 4mm;
  line-height: 1.35;
}
.cover-sub {
  font-size: 12pt;
  color: #47586b;
  line-height: 1.7;
  max-width: 92%;
}
.cover-bar {
  width: 38mm;
  height: 2.8pt;
  background: #0d9488;
  margin: 8mm 0;
}
.cover-box {
  background: #f4f7fa;
  border: 1px solid #d5dfe9;
  border-right: 4pt solid #0d9488;
  border-radius: 8px;
  padding: 5mm 6mm;
  margin-top: 8mm;
}
.cover-box h4 { margin: 0 0 3mm; color: #0c1a2c; font-size: 11pt; }
.cover-box ul { margin: 0; padding-right: 5mm; padding-left: 0; font-size: 9.8pt; color: #334155; }
.cover-box li { margin-bottom: 1.5mm; }
.cover-foot {
  border-top: 1px solid #cbd5e1;
  padding-top: 3.5mm;
  display: flex;
  justify-content: space-between;
  font-size: 8.8pt;
  color: #5b6779;
}

/* Body headings & prose */
h1 { display: none; } /* title is on the cover */
h2 {
  color: #0c1a2c;
  font-size: 14.8pt;
  font-weight: 800;
  margin: 9mm 0 3.5mm;
  padding-bottom: 2.2mm;
  border-bottom: 2pt solid #0d9488;
  page-break-after: avoid;
}
h3 {
  color: #0a7367;
  font-size: 11.8pt;
  font-weight: 700;
  margin: 6mm 0 2mm;
  page-break-after: avoid;
}
p { margin: 2.4mm 0; }
ul, ol { margin: 2.5mm 0; padding-right: 6.5mm; padding-left: 0; }
li { margin: 1.4mm 0; }
strong { color: #0c1a2c; }
hr { border: 0; border-top: 1px solid #dce4ed; margin: 6mm 0; }

code {
  direction: ltr;
  unicode-bidi: isolate;
  font-family: Consolas, "Courier New", monospace;
  font-size: 8.8pt;
  background: #eef4f7;
  color: #0a6157;
  padding: 0.4mm 1.4mm;
  border-radius: 3px;
}
pre {
  direction: ltr;
  text-align: left;
  background: #0f1f33;
  color: #e2e8f0;
  border-radius: 7px;
  padding: 3.6mm 4.5mm;
  margin: 3.5mm 0;
  white-space: pre-wrap;
  overflow-wrap: break-word;
  page-break-inside: avoid;
}
pre code {
  background: transparent;
  color: #e2e8f0;
  padding: 0;
  font-size: 8.3pt;
  line-height: 1.48;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 4mm 0;
  font-size: 9pt;
}
th {
  background: #0c1a2c;
  color: #ffffff;
  text-align: right;
  padding: 2.5mm 3mm;
  font-weight: 700;
}
td {
  padding: 2.3mm 3mm;
  border-bottom: 0.7pt solid #dce4ed;
  vertical-align: top;
}
tr { page-break-inside: avoid; }
tr:nth-child(even) td { background: #f6f9fc; }

blockquote {
  margin: 3.5mm 0;
  padding: 3mm 4.5mm;
  background: #e6f6f4;
  border-right: 3.2pt solid #0d9488;
  border-radius: 4px;
  color: #0c4a42;
}
"""


def build_pdf() -> None:
    md_text = MD_IN.read_text(encoding="utf-8")
    body_html = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists"],
        output_format="html5",
    )

    depi_uri = (ASSETS / "logo-depi.png").as_uri()
    mcit_uri = (ASSETS / "logo-mcit.png").as_uri()
    aegis_uri = (ASSETS / "logo-aegisvapt.png").as_uri()

    html_doc = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>AegisVAPT — دليل الشرح والمناقشة الشامل</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="cover">
    <div>
      <div class="cover-top">
        <div class="logos-left">
          <img class="depi" src="{depi_uri}" alt="DEPI" />
          <img class="aegis" src="{aegis_uri}" alt="AegisVAPT" />
        </div>
        <img class="mcit" src="{mcit_uri}" alt="MCIT" />
      </div>

      <div class="cover-hero">
        <span class="eyebrow">DEPI Graduation Program &middot; Project 5</span>
        <div class="cover-title">الدليل الشامل لشرح مشروع <b>AegisVAPT</b><br/>وورك فلو المناقشة مع المحاضر</div>
        <div class="cover-sub">
          شرح مبسّط خطوة بخطوة لكل مراحل الأسابيع الأربعة، التطويرات الإضافية بعد الخطة،
          خطة العرض والتجربة الحيّة (Live Demo)، وبنك الإجابات النموذجية لأصعب أسئلة المناقشة.
        </div>
        <div class="cover-bar"></div>
        <div class="cover-box">
          <h4>محتويات هذا الدليل:</h4>
          <ul>
            <li><b>الفصل 1 و 2:</b> فكرة المشروع، سبب استخدام موديلين محليين، ومعمارية الـ 5 طبقات.</li>
            <li><b>الفصل 3:</b> شرح تفصيلي مبسّط للأسابيع الأربعة (Recon/AD، Live DVWA/DIVA، التقارير والـ Diff).</li>
            <li><b>الفصل 4:</b> كل التطويرات الزيادة (واجهة AegisVAPT، تحديات الـ 12 ثغرة، Port Solver، والـ 24 اختبار آلي).</li>
            <li><b>الفصل 5 و 6:</b> ورك فلو المناقشة الـ 15 شريحة + سكريبت الـ Live Demo + 12 سؤالًا وجوابًا للمناقشة.</li>
          </ul>
        </div>
      </div>
    </div>

    <div class="cover-foot">
      <span>إعداد: محمد رضا الحداد (<span dir="ltr">@7adadd</span>)</span>
      <span dir="ltr">AegisVAPT v1.0 &middot; 2026-11-27</span>
    </div>
  </div>

  <main>
    {body_html}
  </main>
</body>
</html>"""

    BUILD.mkdir(parents=True, exist_ok=True)
    html_path = BUILD / "defense_guide.html"
    html_path.write_text(html_doc, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.pdf(
            path=str(PDF_OUT),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=(
                "<div style='width:100%;font-size:8px;color:#64748b;padding:0 16mm;"
                "display:flex;justify-content:space-between;font-family:Segoe UI,sans-serif;'>"
                "<span>AegisVAPT &mdash; DEPI Project 5 Defense &amp; Walkthrough Guide</span>"
                "<span><span class='pageNumber'></span> / <span class='totalPages'></span></span>"
                "</div>"
            ),
        )
        browser.close()

    # Spot check PNGs for visual inspection
    png_dir = BUILD / "guide_pngs"
    png_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(str(PDF_OUT))
    for i in range(doc.page_count):
        doc[i].get_pixmap(dpi=115).save(png_dir / f"page-{i + 1:02d}.png")
    print(f"OK PDF -> {PDF_OUT} ({doc.page_count} pages)")


if __name__ == "__main__":
    build_pdf()
