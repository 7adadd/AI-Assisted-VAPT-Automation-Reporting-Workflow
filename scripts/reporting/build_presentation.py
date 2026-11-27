#!/usr/bin/env python3
"""Generate the upgraded 15-slide DEPI Project 5 (AegisVAPT) Defense Presentation (.pptx)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "docs" / "assets"
DELIV_ASSETS = ROOT / "deliverables" / "assets"

NAVY = RGBColor(0x0C, 0x1A, 0x2C)
TEAL = RGBColor(0x0D, 0x94, 0x88)
INK = RGBColor(0x17, 0x25, 0x36)
MUTED = RGBColor(0x5B, 0x67, 0x79)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_BG = RGBColor(0xF4, 0xF7, 0xFA)


def make_benchmark_chart(bench_json: Path, out_png: Path) -> Path:
    records = json.loads(bench_json.read_text(encoding="utf-8"))
    by_model: dict[str, list[dict]] = {}
    for r in records:
        by_model.setdefault(r["model"], []).append(r)

    w, h = 980, 440
    img = Image.new("RGB", (w, h), "#FFFFFF")
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w - 1, h - 1], outline="#D5DBE3", width=2)
    draw.text((30, 20), "Measured Local Model Speed & Grounding Quality (RTX 3050 Ti 4GB)", fill="#0c1a2c")

    models = list(by_model.keys())
    colors = ["#0c1a2c", "#0d9488"]
    bar_x = 80
    chart_bottom = 350
    max_tok = max((r["eval_tok_s"] for r in records), default=50) * 1.15

    tasks = ["T1", "T2", "T3", "T4", "T5", "T6"]
    group_w = 135
    bar_w = 42

    for idx, tid in enumerate(tasks):
        gx = bar_x + idx * group_w
        draw.text((gx + 25, chart_bottom + 12), tid, fill="#172536")
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
        lx = 60 + m_i * 270
        draw.rectangle([lx, 55, lx + 18, 73], fill=colors[m_i % 2])
        avg_tok = sum(x["eval_tok_s"] for x in by_model[m]) / max(len(by_model[m]), 1)
        avg_q = sum(x["auto_grounding_score"] for x in by_model[m]) / max(len(by_model[m]), 1)
        draw.text((lx + 26, 56), f"{m} (avg {avg_tok:.1f} tok/s, {avg_q:.1f}/5)", fill="#172536")

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png)
    return out_png


def add_header(slide, title: str, eyebrow: str = "AegisVAPT | DEPI Project 5"):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.33), Inches(0.12))
    bar.fill.solid()
    bar.fill.fore_color.rgb = TEAL
    bar.line.fill.background()

    aegis_logo = ASSETS / "logo-aegisvapt.png"
    if aegis_logo.exists():
        slide.shapes.add_picture(str(aegis_logo), Inches(12.25), Inches(0.24), height=Inches(0.62))

    tb = slide.shapes.add_textbox(Inches(0.65), Inches(0.26), Inches(11.0), Inches(0.28))
    p = tb.text_frame.paragraphs[0]
    p.text = eyebrow.upper()
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = TEAL

    tb2 = slide.shapes.add_textbox(Inches(0.65), Inches(0.52), Inches(11.4), Inches(0.62))
    p2 = tb2.text_frame.paragraphs[0]
    p2.text = title
    p2.font.size = Pt(25)
    p2.font.bold = True
    p2.font.color.rgb = NAVY


def add_bullets(slide, items: list[str], left=0.68, top=1.42, width=11.9, height=5.4, size=15.5):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"•  {item}"
        p.font.size = Pt(size)
        p.font.color.rgb = INK
        p.space_after = Pt(10)


def add_table_slide(slide, headers: list[str], rows: list[list[str]], top=1.42, row_h=0.48, font_size=11):
    n_rows = len(rows) + 1
    n_cols = len(headers)
    shape = slide.shapes.add_table(n_rows, n_cols, Inches(0.65), Inches(top), Inches(12.0), Inches(min(5.6, n_rows * row_h)))
    tbl = shape.table
    for c, h in enumerate(headers):
        cell = tbl.cell(0, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.size = Pt(font_size + 1)
        p.font.bold = True
        p.font.color.rgb = WHITE
    for r_i, row in enumerate(rows, start=1):
        for c_i, val in enumerate(row):
            cell = tbl.cell(r_i, c_i)
            cell.fill.solid()
            cell.fill.fore_color.rgb = LIGHT_BG if r_i % 2 == 0 else WHITE
            p = cell.text_frame.paragraphs[0]
            p.text = str(val)
            p.font.size = Pt(font_size)
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
    aegis_logo = ASSETS / "logo-aegisvapt.png"
    if depi_logo.exists():
        s1.shapes.add_picture(str(depi_logo), Inches(0.7), Inches(0.45), height=Inches(1.05))
    if aegis_logo.exists():
        s1.shapes.add_picture(str(aegis_logo), Inches(8.6), Inches(0.42), height=Inches(1.02))
    if mcit_logo.exists():
        s1.shapes.add_picture(str(mcit_logo), Inches(10.1), Inches(0.55), height=Inches(0.78))

    accent = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(2.15), Inches(1.6), Inches(0.09))
    accent.fill.solid()
    accent.fill.fore_color.rgb = TEAL
    accent.line.fill.background()

    tb = s1.shapes.add_textbox(Inches(0.7), Inches(2.4), Inches(11.8), Inches(3.2))
    tf = tb.text_frame
    tf.word_wrap = True
    p0 = tf.paragraphs[0]
    p0.text = "AegisVAPT — AI-Assisted VAPT Automation & Reporting Workflow"
    p0.font.size = Pt(34)
    p0.font.bold = True
    p0.font.color.rgb = NAVY

    p2 = tf.add_paragraph()
    p2.text = "DEPI Graduation Program — Project 5 | Privacy-First Local LLMs, Grounded Solver & Human-in-the-Loop QA"
    p2.font.size = Pt(17.5)
    p2.font.color.rgb = MUTED
    p2.space_before = Pt(14)

    p3 = tf.add_paragraph()
    p3.text = "Prepared by: Mohamed Reda Elhaddad (@7adadd)   |   2026-11-27   |   github.com/7adadd"
    p3.font.size = Pt(13.5)
    p3.font.color.rgb = TEAL
    p3.space_before = Pt(24)

    # Slide 2: Problem & Objectives
    s2 = prs.slides.add_slide(blank)
    add_header(s2, "1. Problem Statement & Core Design Principles")
    add_bullets(s2, [
        "VAPT engagements spend 40–60% of analyst hours parsing noisy scan output and drafting repetitive findings.",
        "Cloud LLMs expose sensitive client/lab artifacts externally and fail completely in air-gapped networks.",
        "Unconstrained LLMs fabricate CVEs, non-existent BloodHound edges, and inflated CVSS severity scores.",
        "Our Solution (AegisVAPT): 100% local Ollama inference (llama3.2:3b + qwen2.5:3b) wrapped in deterministic ingest adapters, a 24-prompt grounded library, and a mandatory L1–L4 human validation gate.",
        "Core Principle: AI accelerates triage and drafting — humans and deterministic scripts verify and own every finding.",
    ])

    # Slide 3: 5-Layer Architecture + Workbench
    s3 = prs.slides.add_slide(blank)
    add_header(s3, "2. Layered Workflow Architecture & AegisVAPT Workbench")
    add_table_slide(s3, ["Layer", "Component", "Implementation in Repository", "Anti-Hallucination & Safety Control"], [
        ["Workbench UI", "AegisVAPT Web GUI (127.0.0.1:8000)", "FastAPI + 5 tabs + bundled Chart.js / Cytoscape.js", "Random X-VAPT-Session token + Origin/Host guard + 2 MiB cap"],
        ["L5 Reporting", "Deterministic Math & Docs", "calc_cvss.py, diff_draft.py, build_vapt_report.py", "Exact CVSS 3.1 vector math + word-level AI-vs-Human diff"],
        ["L4 Validation", "Human-in-the-Loop Gate", "deliverables/validation-log.md (L1–L4)", "Data-check + Lab PoC + Dual-Model Cross-Check + Human QA"],
        ["L3 Prompts", "24 Versioned Prompt Templates", "prompts/{recon,ad,web (+PS1),mobile,reporting}", "7-field standard + [source:line] citations + UNKNOWN rule"],
        ["L2 Ingest", "5 Deterministic Parsers", "nmap, enum, bloodhound (+BFS), burp, mobile", "Strips XML/JSON noise; BFS computes exact AD ground truth"],
        ["L1 Runtime", "Local Ollama Loopback (127.0.0.1)", "qwen2.5:3b + llama3.2:3b on RTX 3050 Ti (4 GB)", "vapt_ai.py blocks any non-localhost Ollama URL (Rule P1)"],
    ], row_h=0.62, font_size=10.5)

    # Slide 4: Lab Environment & Ethics
    s4 = prs.slides.add_slide(blank)
    add_header(s4, "3. Local AI Lab Hardware, Dual-Model Strategy & Privacy Gate")
    add_bullets(s4, [
        "Hardware: AMD Ryzen 5 5600H, 16 GB RAM, NVIDIA RTX 3050 Ti Laptop GPU (4 GB VRAM, CUDA active).",
        "Dual-Model Strategy: llama3.2:3b handles rapid triage & executive summaries (~72–81 tok/s); qwen2.5:3b leads structured JSON, AD ACLs, code review & scripts (~57–70 tok/s).",
        "Self-Owned Lab Stack: Kali WSL2 (Nmap, Apache2, PHP 8.4, MariaDB, DVWA), LAB.LOCAL BloodHound graph + BFS Ground Truth, and DIVA APK decompiled via jadx v1.5.6.",
        "Mandatory Privacy & Ethics Rules (P1–P6, E1–E8): zero cloud LLM APIs, gitignored evidence/, non-destructive testing, explicit consent for any PortSwigger POST action.",
    ])

    # Slide 5: Benchmarks Chart
    s5 = prs.slides.add_slide(blank)
    add_header(s5, "4. Week 1 — Real Dual-Model Benchmarks (6 Tasks x 2 Models)")
    chart_png = make_benchmark_chart(bench_json, ROOT / "reports" / "_build" / "bench_chart.png")
    s5.shapes.add_picture(str(chart_png), Inches(0.75), Inches(1.4), width=Inches(11.8))

    # Slide 6: Week 2 Recon & AD (with verified graph visual)
    s6 = prs.slides.add_slide(blank)
    add_header(s6, "5. Week 2 — Recon & Active Directory Analysis (BFS Ground Truth)")
    add_bullets(s6, [
        "Real Kali WSL Nmap XML + HTTP banners parsed cleanly via nmap_to_context.py and enum_to_context.py.",
        "BloodHound LAB.LOCAL (11 nodes, 8 edges) solved deterministically by BFS before prompting AI:",
        "Path 1: m.ali -> GenericAll -> svc-backup -> MemberOf -> IT-Admins -> WriteDacl -> Domain Admins.",
        "Path 2: j.smith (AS-REP) -> ForceChangePassword -> svc-sync -> DCSync -> LAB.LOCAL.",
        "Generated & verified 4 audit scripts (PS1 AST + Python run).",
        f"Week 2 Log: {stats['week2_summary']}",
    ], left=0.65, top=1.42, width=5.95, height=5.5, size=14)
    graph_shot = DELIV_ASSETS / "gui-smoke-graph.png"
    if graph_shot.exists():
        s6.shapes.add_picture(str(graph_shot), Inches(6.75), Inches(1.42), width=Inches(5.95))

    # Slide 7: Week 3 Web
    s7 = prs.slides.add_slide(blank)
    add_header(s7, "6. Week 3 — Web Application Analysis on Live DVWA (5 Validated PoCs)")
    add_table_slide(s7, ["Module", "Parameter", "AI-Assisted Payload (Passed W5 Safety Gate)", "Verified Live Proof"], [
        ["SQL Injection", "id", "1' UNION SELECT user,password FROM users-- -", "poc-01-sqli.png (Extracted user MD5 hashes)"],
        ["Reflected XSS", "name", "<script>alert('XSS-R')</script>", "poc-02-xss-reflected.png (Playwright alert fired)"],
        ["Stored XSS", "mtxMessage", "<script>alert('XSS-S')</script>", "poc-03-xss-stored.png (Persisted guestbook trigger)"],
        ["Command Injection", "ip", "127.0.0.1; id", "poc-04-cmdi.png (uid=33(www-data) confirmed)"],
        ["Local File Inclusion", "page", "../../../../../../etc/passwd", "poc-05-lfi.png (root:x:0:0 read verified)"],
    ], row_h=0.62)

    # Slide 8: Week 3 Mobile
    s8 = prs.slides.add_slide(blank)
    add_header(s8, "7. Week 3 — Mobile Static Analysis (DIVA APK via jadx + Frida)")
    add_bullets(s8, [
        "Decompiled diva-beta.apk with jadx v1.5.6 into 718 Java classes & AndroidManifest.xml.",
        "M1/M3 extracted grounded defects with exact source lines: HardcodeActivity.java:19 ('vendorsecretkey'), LogActivity.java:23 (CC logcat leak), InsecureDataStorage1Activity.java:20, AndroidManifest.xml (debuggable & allowBackup).",
        "Generated 2 Frida JS scripts (M2): frida_ssl_pinning_bypass.js and frida_diva_hardcode_hook.js.",
        "Static Verification: validated JS syntax and exact Java class/method signatures against decompiled code (static verification only; emulator runtime left as next step).",
        f"Week 3 Log: {stats['week3_summary']}",
    ])

    # Slide 9: Week 4 Reporting & Diff
    s9 = prs.slides.add_slide(blank)
    add_header(s9, "8. Week 4 — AI Draft vs. Human-Edited VAPT Report & QA Diff")
    add_bullets(s9, [
        f"Drafted 9 findings via RP1–RP4 (vapt-report-ai-draft.md), then executed full human QA & deterministic verification.",
        f"Deterministic Diff (diff_draft.py): {stats['diff_summary']}",
        "Key Human Fixes: recomputed all 9 CVSS v3.1 scores with calc_cvss.py (1 Critical 9.8, 4 High, 4 Medium), cut 339 ungrounded words, and embedded 5 live DVWA PoC screenshots.",
        "Deliverables Generated: Branded DEPI VAPT Report (PDF/DOCX), Reusable SOP (PDF/DOCX), Master Documentation PDF, and Defense Deck.",
    ])

    # Slide 10: Hallucination Check Summary
    s10 = prs.slides.add_slide(blank)
    add_header(s10, "9. Cross-Phase Hallucination & Validation Accuracy Audit")
    add_table_slide(s10, ["Week / Phase", "Claims Checked", "Verified (✅)", "Partial (⚠️)", "Hallucinated (❌)", "Net Result"], stats["accuracy_rows"], row_h=0.58)
    add_bullets(s10, [
        "Combined Weeks 2–3 Validation Log (24 claims): 13 Strictly Verified (54.2%), 5 Partial Corrected (20.8%), 6 Rejected Hallucinations (25.0%) -> 75.0% Usable Output & 0% Hallucinations Leaked to Final Report.",
    ], top=5.35, height=1.2, size=14)

    # Slide 11: Post-Plan Upgrade 1 - AegisVAPT GUI
    s11 = prs.slides.add_slide(blank)
    add_header(s11, "10. Post-Plan Upgrade — AegisVAPT Local Web Workbench")
    add_bullets(s11, [
        "Single-command localhost FastAPI studio (python run_gui.py) bound strictly to 127.0.0.1:8000.",
        "5 Specialized Tabs: Artifact Analyzer (+ Cross-Model Arena), Port Solver, Telemetry Dashboard, AD Attack Graph, Reports & Export.",
        "Zero-CDN Privacy UI: Chart.js and Cytoscape.js bundled locally in app/static/vendor/.",
        "Security Hardening: per-launch X-VAPT-Session token, Origin/Host checks (blocks CSRF & DNS rebinding), and 2 MiB upload limit.",
    ], left=0.65, top=1.42, width=5.65, height=5.4, size=14)
    dash_shot = DELIV_ASSETS / "gui-smoke-dashboard.png"
    if dash_shot.exists():
        s11.shapes.add_picture(str(dash_shot), Inches(6.45), Inches(1.42), width=Inches(6.25))

    # Slide 12: Post-Plan Upgrade 2 - 12-Challenge Suite
    s12 = prs.slides.add_slide(blank)
    add_header(s12, "11. Post-Plan Upgrade — 12-Challenge DVWA & PortSwigger Suite")
    add_table_slide(s12, ["Suite", "Evaluated Patterns (Passive HTTP Triage via W1 on qwen2.5:3b)", "Speed Range", "Result"], [
        ["DVWA (6/6)", "SQLi UNION, Reflected XSS, Stored XSS, OS Command Injection, LFI Traversal, CSRF", "56.9–68.9 tok/s", "6 / 6 Diagnosed (Heuristic + Citation)"],
        ["PortSwigger (6/6)", "SSRF Stock Check, XXE External Entity, SSTI Template Inj, IDOR, JWT alg=none, Blind SQLi Cookie", "68.4–70.5 tok/s", "6 / 6 Diagnosed (Heuristic + Citation)"],
        ["Combined Total", "12 local .http challenges with target parameters & [http:line] evidence citations", "Avg ~66.8 tok/s", "12 / 12 Passive Triage (100% Heuristic)"],
    ], row_h=0.72)
    add_bullets(s12, [
        "Every challenge is loadable with one click from the Dashboard straight into the Analyzer for live side-by-side Qwen vs Llama inspection.",
        "Honest scope note: automatic evaluator signals are heuristic keyword + citation checks and still require human adjudication in live testing.",
    ], top=4.75, height=1.8, size=14.5)

    # Slide 13: Post-Plan Upgrade 3 - Agentic Port Solver & Offline Tests
    s13 = prs.slides.add_slide(blank)
    add_header(s13, "12. Post-Plan Upgrade — Grounded Port Solver & Automated Tests")
    add_bullets(s13, [
        "Added Prompt PS1, lab_inspect.py (passive GET surface mapper), agentic_solver.py, port_solver.py & safe_lab_http.py.",
        "Observe -> Reason -> Act -> Verify loop with XML entity encoding & WAF feedback adaptation.",
        "Strict Safety Guardrails: *.web-security-academy.net allowlist, SSRF IP/loopback/metadata block, redirect host pin, explicit GUI consent checkbox for POST.",
        "Honest State Machine: separates solved (official confirmation), attempted, not_solved, blocked & expired.",
        "Automated Assurance: 24 deterministic offline unit & API tests + Playwright E2E GUI check.",
    ], left=0.65, top=1.42, width=6.15, height=5.5, size=13.8)
    solver_shot = DELIV_ASSETS / "gui-smoke-solver.png"
    if solver_shot.exists():
        s13.shapes.add_picture(str(solver_shot), Inches(6.95), Inches(1.42), width=Inches(5.75))

    # Slide 14: Live Demo Plan
    s14 = prs.slides.add_slide(blank)
    add_header(s14, "13. Instructor Live Demo Plan (3 Minutes)")
    add_bullets(s14, [
        "Step 1 (30s — CLI & Math): Run calc_cvss.py on CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H -> verify exact 8.8 High determinism.",
        "Step 2 (40s — Dashboard): Open http://127.0.0.1:8000 -> inspect Ollama status pill, KPIs (24 prompts, 12 challenges, 54.2%/75.0%), benchmark charts.",
        "Step 3 (45s — Analyzer Arena): Click Load on dvwa-01 SQLi -> Compare both models (Qwen vs Llama) -> demonstrate live [http:line] citations & Human Verdict buttons.",
        "Step 4 (35s — AD Graph): Open AD Attack Paths -> highlight BFS shortest paths on LAB.LOCAL and click a node for edges.",
        "Step 5 (30s — Reports & Deliverables): Open Reports & Export -> inspect 10.3% diff metrics, 5 PoC screenshots, and Human-Edited VAPT Report PDF.",
    ], size=14.5)

    # Slide 15: Lessons Learned, Limitations & Final Closure
    s15 = prs.slides.add_slide(blank)
    add_header(s15, "14. Lessons Learned, Honest Limitations & Final Deliverables")
    add_bullets(s15, [
        "3B local models fit comfortably in 4 GB VRAM (57–81 tok/s) when paired with noise-stripping ingest adapters and strict [source:line] grounding.",
        "Dual-model cross-checking + mathematical tools (BFS, AST check, calc_cvss.py, diff_draft.py) eliminate single-model blind spots.",
        "Honest Scope Boundaries: AD ran on a structured LAB.LOCAL graph + BFS solver; Mobile DIVA was static/signature-verified via jadx; 12-challenge suite is passive triage.",
        "Final Package Ready: VAPT Report (PDF/DOCX), Reusable SOP (PDF/DOCX), Master Documentation PDF, AegisVAPT Workbench, 15-Slide Deck, and Arabic Defense Guide PDF.",
    ], size=14.5)

    out_pptx.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_pptx))
    print(f"OK PPTX -> {out_pptx} ({len(prs.slides)} slides)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", default=str(ROOT / "evidence" / "week4" / "presentation-stats.json"))
    ap.add_argument("--bench", default=str(ROOT / "evidence" / "week1" / "benchmark-raw.json"))
    ap.add_argument("--out", default=str(ROOT / "deliverables" / "DEPI-Project5-Presentation.pptx"))
    args = ap.parse_args()
    build_deck(Path(args.stats), Path(args.bench), Path(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
