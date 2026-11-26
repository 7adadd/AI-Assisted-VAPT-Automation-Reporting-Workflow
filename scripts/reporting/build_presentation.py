#!/usr/bin/env python3
"""Generate the DEPI Project 5 Presentation (.pptx) from real measured project data."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "docs" / "assets"

NAVY = RGBColor(0x16, 0x27, 0x3D)
TEAL = RGBColor(0x0F, 0x7B, 0x6C)
INK = RGBColor(0x1F, 0x29, 0x37)
MUTED = RGBColor(0x5B, 0x67, 0x79)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_BG = RGBColor(0xF6, 0xF8, 0xFA)


def make_benchmark_chart(bench_json: Path, out_png: Path) -> Path:
    records = json.loads(bench_json.read_text(encoding="utf-8"))
    by_model = {}
    for r in records:
        m = r["model"]
        by_model.setdefault(m, []).append(r)

    w, h = 980, 440
    img = Image.new("RGB", (w, h), "#FFFFFF")
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w - 1, h - 1], outline="#D5DBE3", width=2)

    draw.text((30, 20), "Measured Local Model Speed & Grounding Quality (RTX 3050 Ti 4GB)", fill="#16273d")

    models = list(by_model.keys())
    colors = ["#16273d", "#0f7b6c"]
    bar_x = 80
    chart_bottom = 350
    max_tok = max((r["eval_tok_s"] for r in records), default=50) * 1.15

    tasks = ["T1", "T2", "T3", "T4", "T5", "T6"]
    group_w = 135
    bar_w = 42

    for idx, tid in enumerate(tasks):
        gx = bar_x + idx * group_w
        draw.text((gx + 25, chart_bottom + 12), tid, fill="#1f2937")
        for m_i, m in enumerate(models[:2]):
            rec = next((x for x in by_model[m] if x["task_id"] == tid), None)
            val = rec["eval_tok_s"] if rec else 0
            score = rec["auto_grounding_score"] if rec else 0
            bh = int((val / max_tok) * 230) if max_tok else 0
            x0 = gx + m_i * (bar_w + 8)
            y0 = chart_bottom - bh
            draw.rectangle([x0, y0, x0 + bar_w, chart_bottom], fill=colors[m_i % 2])
            draw.text((x0 + 2, y0 - 18), f"{val:.0f}t/s", fill=colors[m_i % 2])
            draw.text((x0 + 4, chart_bottom + 32 + m_i * 16), f"{score}/5", fill=colors[m_i % 2])

    draw.line([60, chart_bottom, w - 40, chart_bottom], fill="#94a3b8", width=2)
    for m_i, m in enumerate(models[:2]):
        lx = 60 + m_i * 250
        draw.rectangle([lx, 55, lx + 18, 73], fill=colors[m_i % 2])
        avg_tok = sum(x["eval_tok_s"] for x in by_model[m]) / max(len(by_model[m]), 1)
        avg_q = sum(x["auto_grounding_score"] for x in by_model[m]) / max(len(by_model[m]), 1)
        draw.text((lx + 26, 56), f"{m} (avg {avg_tok:.1f} tok/s, {avg_q:.1f}/5)", fill="#1f2937")

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png)
    return out_png


def add_header(slide, title: str, eyebrow: str = "DEPI Project 5 | AI-Assisted VAPT Workflow"):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.33), Inches(0.12))
    bar.fill.solid()
    bar.fill.fore_color.rgb = TEAL
    bar.line.fill.background()

    tb = slide.shapes.add_textbox(Inches(0.65), Inches(0.28), Inches(11.5), Inches(0.3))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.text = eyebrow.upper()
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = TEAL

    tb2 = slide.shapes.add_textbox(Inches(0.65), Inches(0.55), Inches(12.0), Inches(0.65))
    tf2 = tb2.text_frame
    p2 = tf2.paragraphs[0]
    p2.text = title
    p2.font.size = Pt(26)
    p2.font.bold = True
    p2.font.color.rgb = NAVY


def add_bullets(slide, items: list[str], left=0.7, top=1.45, width=11.8, height=5.3, size=16):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"•  {item}"
        p.font.size = Pt(size)
        p.font.color.rgb = INK
        p.space_after = Pt(10)


def add_table_slide(slide, headers: list[str], rows: list[list[str]], top=1.45, row_h=0.48):
    n_rows = len(rows) + 1
    n_cols = len(headers)
    shape = slide.shapes.add_table(n_rows, n_cols, Inches(0.65), Inches(top), Inches(12.0), Inches(min(5.5, n_rows * row_h)))
    tbl = shape.table
    for c, h in enumerate(headers):
        cell = tbl.cell(0, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = WHITE
    for r_i, row in enumerate(rows, start=1):
        for c_i, val in enumerate(row):
            cell = tbl.cell(r_i, c_i)
            cell.fill.solid()
            cell.fill.fore_color.rgb = LIGHT_BG if r_i % 2 == 0 else WHITE
            p = cell.text_frame.paragraphs[0]
            p.text = str(val)
            p.font.size = Pt(11)
            p.font.color.rgb = INK


def build_deck(stats_json: Path, bench_json: Path, out_pptx: Path) -> None:
    stats = json.loads(stats_json.read_text(encoding="utf-8"))
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    # Slide 1: Title
    s1 = prs.slides.add_slide(blank)
    depi_logo = ASSETS / "logo-depi.png"
    mcit_logo = ASSETS / "logo-mcit.png"
    if depi_logo.exists():
        s1.shapes.add_picture(str(depi_logo), Inches(0.7), Inches(0.45), height=Inches(1.05))
    if mcit_logo.exists():
        s1.shapes.add_picture(str(mcit_logo), Inches(10.3), Inches(0.55), height=Inches(0.75))

    accent = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(2.25), Inches(1.4), Inches(0.08))
    accent.fill.solid()
    accent.fill.fore_color.rgb = TEAL
    accent.line.fill.background()

    tb = s1.shapes.add_textbox(Inches(0.7), Inches(2.5), Inches(11.8), Inches(2.6))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "AI-Assisted VAPT Automation & Reporting Workflow"
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = NAVY

    p2 = tf.add_paragraph()
    p2.text = "DEPI Graduation Program — Project 5 | Privacy-First Local LLMs + Human-in-the-Loop Validation"
    p2.font.size = Pt(18)
    p2.font.color.rgb = MUTED
    p2.space_before = Pt(14)

    p3 = tf.add_paragraph()
    p3.text = "Prepared by: Mohamed Reda Elhaddad (@7adadd)  |  Date: 2026-11-26"
    p3.font.size = Pt(14)
    p3.font.color.rgb = TEAL
    p3.space_before = Pt(24)

    # Slide 2: Problem & Objectives
    s2 = prs.slides.add_slide(blank)
    add_header(s2, "1. Problem Statement & Core Design Principles")
    add_bullets(s2, [
        "VAPT engagements spend 40–60% of analyst hours parsing noisy tool output and drafting repetitive reports.",
        "Cloud LLMs introduce unacceptable client-data leakage risks and fail inside air-gapped lab networks.",
        "Unconstrained LLMs hallucinate CVEs, non-existent BloodHound attack edges, and inflated CVSS scores.",
        "Our Solution: 100% local Ollama inference (Llama 3.2 + Qwen 2.5) wrapped in deterministic ingest adapters and a mandatory L1–L4 human validation gate.",
        "Core Rule: AI accelerates triage and drafting — humans execute, verify, and own every finding.",
    ])

    # Slide 3: 5-Layer Architecture
    s3 = prs.slides.add_slide(blank)
    add_header(s3, "2. 5-Layer Workflow Architecture")
    add_table_slide(s3, ["Layer", "Component", "Implementation in Repo", "Security / Anti-Hallucination Control"], [
        ["L1 Runtime", "Local Ollama Server (127.0.0.1:11434)", "llama3.2:3b + qwen2.5:3b on RTX 3050 Ti", "vapt_ai.py blocks any non-localhost URL (Rule P1)"],
        ["L2 Ingest", "5 Deterministic Parsers", "nmap, enum, bloodhound (+BFS), burp, mobile", "Strips noise and attaches [source:line/id] tags"],
        ["L3 Prompts", "23 Versioned Templates", "prompts/{recon,active-directory,web,mobile,reporting}", "7-field standard + mandatory Grounding Block"],
        ["L4 Validation", "Human-in-the-Loop Gate", "evidence/validation-log.md (L1–L4)", "Data-check + Lab PoC + Cross-Model Check + QA"],
        ["L5 Reporting", "Automated Doc & Diff Pipeline", "calc_cvss.py, build_vapt_report.py, diff_draft.py", "Exact CVSS 3.1 math + AI-vs-Human word diff"],
    ], row_h=0.65)

    # Slide 4: Lab Environment & Ethics
    s4 = prs.slides.add_slide(blank)
    add_header(s4, "3. Local AI Lab & Privacy / Ethics Gate")
    add_bullets(s4, [
        "Hardware: AMD Ryzen 5 5600H, 16 GB RAM, NVIDIA RTX 3050 Ti (4 GB VRAM, CUDA active).",
        "Dual-Model Strategy: llama3.2:3b (fast prose/triage) + qwen2.5:3b (structured JSON, code & script generation).",
        "Target Lab Stack (Isolated Self-Owned): Kali WSL (Nmap, Apache2, MariaDB, DVWA), BloodHound AD Lab Dataset + BFS Solver, DIVA Android APK (jadx).",
        "Mandatory Privacy & Ethics Checklist (Doc 03): zero cloud APIs, gitignored raw evidence, pre-push scan, non-destructive PoCs only.",
    ])

    # Slide 5: Benchmarks Chart
    s5 = prs.slides.add_slide(blank)
    add_header(s5, "4. Week 1 — Real Model Benchmarks (6 Fixed Tasks)")
    chart_png = make_benchmark_chart(bench_json, ROOT / "reports" / "_build" / "bench_chart.png")
    s5.shapes.add_picture(str(chart_png), Inches(0.75), Inches(1.4), width=Inches(11.8))

    # Slide 6: Week 2 Recon & AD
    s6 = prs.slides.add_slide(blank)
    add_header(s6, "5. Week 2 — AI for Recon & Active Directory Analysis")
    add_bullets(s6, [
        "Real Kali WSL Nmap XML + service banners parsed by nmap_to_context.py and enum_to_context.py.",
        "BloodHound AD lab graph (LAB.LOCAL) solved deterministically by BFS (bloodhound_to_context.py) as Ground Truth.",
        "Verified 2 multi-hop paths: m.ali -> GenericAll -> svc-backup (Kerberoastable) -> IT-Admins -> WriteDacl -> Domain Admins; j.smith (AS-REP) -> ForceChangePassword -> svc-sync -> GetChangesAll (DCSync).",
        "Generated & verified 4 audit scripts in scripts/generated/ (PowerShell AST-checked + Python executed against lab data).",
        f"Week 2 Validation Accuracy: {stats['week2_summary']}",
    ])

    # Slide 7: Week 3 Web
    s7 = prs.slides.add_slide(blank)
    add_header(s7, "6. Week 3 — Web Analysis on Live DVWA (5 Validated PoCs)")
    add_table_slide(s7, ["Module", "Parameter", "AI-Assisted Payload Validated", "Proof"], [
        ["SQL Injection", "id", "1' UNION SELECT user,password FROM users-- -", "poc-sqli.png (MD5 hashes extracted)"],
        ["Reflected XSS", "name", "<script>alert('XSS-R')</script>", "poc-xss-r.png (Dialog triggered)"],
        ["Stored XSS", "mtxMessage", "<script>alert('XSS-S')</script>", "poc-xss-s.png (Persisted payload)"],
        ["Command Injection", "ip", "127.0.0.1; id", "poc-cmdi.png (uid=33(www-data))"],
        ["Local File Inclusion", "page", "../../../../../../etc/passwd", "poc-lfi.png (root:x:0:0 read)"],
    ], row_h=0.62)

    # Slide 8: Week 3 Mobile
    s8 = prs.slides.add_slide(blank)
    add_header(s8, "7. Week 3 — Mobile Analysis (DIVA APK + Frida Scripts)")
    add_bullets(s8, [
        "Decompiled diva-beta.apk via jadx CLI into real Java source & AndroidManifest.xml.",
        "M1/M3 prompts cited exact source lines: HardcodeActivity.java (hardcoded 'vendorsecretkey'), LogActivity.java (sensitive logcat leak), InsecureDataStorage1Activity.java (plaintext SharedPreferences), AndroidManifest.xml (exported activities).",
        "Generated 2 Frida scripts via M2: frida_ssl_pinning_bypass.js and frida_diva_hardcode_hook.js.",
        "Verified JS syntax + exact class/method signatures (jakhar.aseem.diva.HardcodeActivity.access) against decompiled code.",
        f"Week 3 Validation Accuracy: {stats['week3_summary']}",
    ])

    # Slide 9: Week 4 Reporting & Diff
    s9 = prs.slides.add_slide(blank)
    add_header(s9, "8. Week 4 — AI Draft vs. Human-Edited Report & QA Diff")
    add_bullets(s9, [
        f"Generated full AI draft report from {stats['finding_count']} validated findings (RP1–RP4), then performed human QA + CVSS verification.",
        f"Deterministic Word-Level Diff (diff_draft.py): {stats['diff_summary']}",
        "Key Human Corrections Caught: CVSS vector math fixes via calc_cvss.py, removal of ungrounded claims, and insertion of exact PoC screenshots.",
        "Delivered branded DEPI PDF + DOCX reports and a standalone Reusable Workflow SOP.",
    ])

    # Slide 10: Hallucination Check Summary
    s10 = prs.slides.add_slide(blank)
    add_header(s10, "9. Cross-Phase Hallucination & Accuracy Review")
    add_table_slide(s10, ["Week / Phase", "Claims Checked", "Verified (✅)", "Partial (⚠️)", "Hallucinated (❌)", "Accuracy %"], stats["accuracy_rows"], row_h=0.6)

    # Slide 11: Live Demo Script
    s11 = prs.slides.add_slide(blank)
    add_header(s11, "10. Live Demo Plan (3 Minutes)")
    add_bullets(s11, [
        "Step 1 (45s): Run python scripts/ingest/nmap_to_context.py evidence/week2/nmap-lab.xml -> show clean [nmap:port] context.",
        "Step 2 (60s): Run python scripts/vapt_ai.py --template R1 --var-file nmap_xml_summary=... --cross-check -> show live local Llama vs Qwen comparison.",
        "Step 3 (45s): Show calc_cvss.py verifying a CVSS 3.1 vector + diff_draft.py output catching an AI exaggeration.",
        "Step 4 (30s): Open Human-Edited VAPT Report PDF with embedded live DVWA PoC screenshots & Reusable SOP.",
    ])

    # Slide 12: Lessons Learned & Limitations
    s12 = prs.slides.add_slide(blank)
    add_header(s12, "11. Lessons Learned & Honest Scope Limitations")
    add_bullets(s12, [
        "3B local models fit 4 GB VRAM cleanly (~40–80 tok/s) and excel when fed noise-stripped ingest context.",
        "Grounding rules + [source:line] citations cut hallucinations sharply, but CVSS math and exploit verification MUST stay deterministic/human.",
        "Limitations: AD phase validated against structured lab dataset + BFS solver; Mobile Frida scripts verified against decompiled jadx signatures (ready for USB/emulator runtime).",
        "Next Steps: Expand ingest adapters (Nuclei, ffuf) and add automated unit tests for prompt regression.",
    ])

    out_pptx.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_pptx))
    print(f"OK PPTX -> {out_pptx}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", required=True)
    ap.add_argument("--bench", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    build_deck(Path(args.stats), Path(args.bench), Path(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
