# Reusable AI-Assisted VAPT Workflow Standard Operating Procedure (SOP)

**Document ID:** SOP-VAPT-AI-01  
**Project:** AI-Assisted VAPT Automation & Reporting Workflow (DEPI Project 5)  
**Author:** Mohamed Reda Elhaddad (`@7adadd`)  
**Applicability:** Authorized penetration testing and isolated security lab engagements  

---

## 1. Purpose & Core Principle

This Standard Operating Procedure (SOP) defines a **repeatable, privacy-first, human-in-the-loop** workflow for using locally-hosted Large Language Models (LLMs) across all five phases of a VAPT engagement:

1. **Reconnaissance**
2. **Active Directory Analysis**
3. **Web Application Testing**
4. **Mobile Application Analysis**
5. **Reporting & Quality Assurance**

> **Non-Negotiable Rule:** AI is an accelerator, never an autonomous operator. Every AI claim, script, payload, attack path, and CVSS vector must pass manual validation (`L1–L4`) before entering a client or lab report.

---

## 2. Architecture Overview (5 Layers)

```text
+-----------------------------------------------------------------------+
| L5  REPORTING PIPELINE                                                |
|     calc_cvss.py + build_vapt_report.py (PDF/DOCX) + diff_draft.py    |
+-----------------------------------------------------------------------+
| L4  HUMAN VALIDATION GATE                                             |
|     L1 Data-Verified | L2 Lab-Executed | L3 Cross-Model | L4 QA       |
+-----------------------------------------------------------------------+
| L3  VERSIONED PROMPT LIBRARY (23 templates in prompts/<phase>/)       |
|     7-field standard + mandatory Grounding Rules + UNKNOWN fallback   |
+-----------------------------------------------------------------------+
| L2  DETERMINISTIC INGEST ADAPTERS (scripts/ingest/*.py)               |
|     Nmap XML | Enum text | BloodHound JSON (+BFS) | HTTP | jadx/Java  |
+-----------------------------------------------------------------------+
| L1  LOCAL AI RUNTIME (Ollama @ http://127.0.0.1:11434)                |
|     llama3.2:3b (triage & prose) + qwen2.5:3b (code, JSON, scripts)   |
+-----------------------------------------------------------------------+
```

---

## 3. Mandatory Pre-Engagement Gate (Privacy & Ethics)

Before running any scan or prompt:

1. **Authorization Check (Rule E1):** Confirm written authorization or verify that targets are strictly inside the self-owned isolated lab (`127.0.0.1`, Kali WSL, `LAB.LOCAL` dataset, DIVA APK).
2. **Local-Only Runtime Check (Rule P1):** Verify Ollama is bound to `127.0.0.1:11434` and no cloud API keys are configured. `scripts/vapt_ai.py` enforces this programmatically and aborts if a non-local URL is passed.
3. **Repository Hygiene Check (Rule P3/P4):** Ensure raw tool dumps (`evidence/`) and intermediate builds (`reports/_build/`) remain in `.gitignore`.
4. **Non-Destructive Scope (Rule E6):** Run read-only enumeration first; review every AI-generated script line-by-line before execution.

---

## 4. Phase-by-Phase Execution Procedure

### Phase 1 — Reconnaissance
1. Run Nmap with XML output (`nmap -sV -sC -oA evidence/week2/nmap-lab <target>`) and banner checks (`enum-lab.txt`).
2. Strip XML noise using deterministic ingest:
   ```bash
   python scripts/ingest/nmap_to_context.py evidence/week2/nmap-lab.xml --out evidence/week2/nmap_context.txt
   python scripts/ingest/enum_to_context.py evidence/week2/enum-lab.txt --out evidence/week2/enum_context.txt
   ```
3. Run templates `R1` (triage), `R2` (service deep-dive), and `R3` (enumeration planner) via `scripts/vapt_ai.py`.
4. **Validation Gate (L1):** Verify every cited port, service banner, and version against `nmap-lab.xml`.

### Phase 2 — Active Directory Analysis
1. Ingest BloodHound JSON and compute deterministic BFS shortest paths as mathematical Ground Truth:
   ```bash
   python scripts/ingest/bloodhound_to_context.py lab/ad-lab-dataset/bloodhound_lab.json \
     --out evidence/week2/bloodhound_context.txt \
     --ground-truth-out evidence/week2/bloodhound_ground_truth.json
   ```
2. Run `AD1` (attack paths) with `--cross-check` (`llama3.2:3b` + `qwen2.5:3b`), plus `AD2` (ACL dump), `AD4` (enum4linux), and `AD5` (Kerberoasting/AS-REP).
3. Generate read-only audit scripts with `AD3` (`--model qwen2.5:3b`).
4. **Validation Gate (L1 + L2 + L3):**
   - Compare every AI-claimed hop against `bloodhound_ground_truth.json`.
   - Parse PowerShell scripts with the PowerShell AST parser and execute Python audit scripts in the lab before trusting output.

### Phase 3 — Web Application Testing
1. Capture raw HTTP request/response pairs from Burp Suite or lab test scripts into `evidence/week3/requests/`.
2. Convert to line-numbered context:
   ```bash
   python scripts/ingest/burp_to_context.py evidence/week3/requests/01-sqli-request.txt \
     --out evidence/week3/context-01-sqli-request.txt
   ```
3. Run `W1` (request explainer), `W2` (payload suggester), `W3` (response analyzer), and **mandatory `W5` (payload safety review)** before running anything.
4. **Validation Gate (L2):** Execute approved non-destructive payloads in DVWA, capture PoC screenshots, and log both succeeded and failed payloads in `evidence/validation-log.md`.

### Phase 4 — Mobile Application Analysis
1. Decompile the target APK with `jadx`:
   ```bash
   jadx.bat -d evidence/week3/diva-src lab/mobile/diva-beta.apk
   ```
2. Extract line-numbered snippets from `AndroidManifest.xml` and suspicious `.java` classes:
   ```bash
   python scripts/ingest/mobile_to_context.py evidence/week3/diva-src/resources/AndroidManifest.xml \
     --out evidence/week3/context-manifest.txt
   ```
3. Run `M1` (code review), `M3` (manifest analysis), `M4` (confirmation plan), and `M2` (Frida script generation) using `qwen2.5:3b` (plus `--cross-check` on `M1`/`M3`).
4. **Validation Gate (L1/L2):** Verify every cited Java line number in the decompiled source, check Frida JS syntax (`node --check` or JS parser), and confirm exact package/class/method signatures before running `frida -U -f <pkg> -l <script>.js`.

### Phase 5 — Reporting & Quality Assurance
1. Draft individual findings (`RP1`), preliminary CVSS vectors (`RP2`), Executive Summary (`RP3`), and Remediation Roadmap (`RP4`) strictly from validated PoC notes.
2. **Mandatory Human QA Pass (L4):**
   - Recompute every CVSS v3.1 vector deterministically:
     ```bash
     python scripts/reporting/calc_cvss.py "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H"
     ```
   - Remove any ungrounded claims, exaggerated impacts, or invented details.
   - Insert exact PoC screenshots and the AI-assistance disclosure (Ethics Rule E7).
3. Compute the deterministic AI-vs-Human diff audit:
   ```bash
   python scripts/reporting/diff_draft.py deliverables/vapt-report-ai-draft.md \
     deliverables/vapt-report-human-edited.md \
     --out deliverables/week4-hallucination-check-and-diff.md
   ```
4. Render branded PDF and DOCX deliverables:
   ```bash
   python scripts/reporting/build_vapt_report.py deliverables/vapt-report-human-edited.md \
     --pdf deliverables/VAPT-Report-Human-Edited.pdf \
     --docx deliverables/VAPT-Report-Human-Edited.docx \
     --title "VAPT Assessment Report (Human-Edited Final)"
   ```

---

## 5. Model Routing Guide (Based on Measured Lab Benchmarks)

| Task Type | Primary Model | Secondary (Cross-Check) | Reason |
|---|---|---|---|
| Recon triage & Executive prose (`R1`, `R4`, `RP3`) | `llama3.2:3b` | `qwen2.5:3b` | Fast generation + clear English summaries |
| Structured JSON / BloodHound / ACL (`AD1`, `AD2`, `M3`) | `qwen2.5:3b` | `llama3.2:3b` | Stronger structured reasoning & citation adherence |
| Code review & Script generation (`AD3`, `M1`, `M2`) | `qwen2.5:3b` | — | Better syntax accuracy in PowerShell/Java/Frida JS |
| High-impact claims & CVSS (`AD1`, `RP2`) | Both (`--cross-check`) | Human + `calc_cvss.py` | Detects discrepancies/hallucinations early |

---

## 6. Validation Verdict Standard

Every evaluated AI claim is logged in `evidence/validation-log.md` using four verdicts:
- `✅ VERIFIED` — Confirmed by raw data (`L1`), lab execution (`L2`), or cross-model + human check (`L3/L4`).
- `⚠️ PARTIAL` — Core direction valid, but required human correction (e.g., wrong line number, minor cmdlet flag, or adjusted CVSS metric).
- `❌ HALLUCINATION` — Contradicted by ground truth or ungrounded invention; discarded and logged.
- `❔ UNKNOWN` — Model correctly refused to guess due to insufficient `<DATA>`.

---

## 7. Pre-Push Checklist (Mandatory Before `git push`)

- [ ] `git status` shows no `evidence/` raw dumps, `.apk` binaries, or `reports/_build/` files.
- [ ] All pushed reports contain only isolated lab identifiers (`127.0.0.1`, `LAB.LOCAL`, `DVWA`, `DIVA`).
- [ ] All scripts execute cleanly and CVSS scores match `calc_cvss.py` output.
