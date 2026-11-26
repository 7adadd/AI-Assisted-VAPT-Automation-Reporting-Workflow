# AI-Assisted VAPT Automation & Reporting Workflow

**DEPI Graduation Program — Project 5**

A privacy-first, human-in-the-loop workflow that uses **locally-hosted LLMs** (Ollama / LM Studio / GPT4All) to assist every phase of a Vulnerability Assessment & Penetration Testing (VAPT) engagement — from reconnaissance and Active Directory analysis to web/mobile testing and professional report writing.

> **Core principle:** AI accelerates the analyst — it never replaces human validation.
> Every AI output (attack paths, payloads, scripts, report text) is **verified manually in an isolated lab** before it is trusted.

---

## Why local models?

| Benefit | Meaning |
|---|---|
| **Privacy** | Client / lab data never leaves the machine — no cloud APIs |
| **Offline** | Works inside isolated, air-gapped lab networks |
| **Reproducible** | Same model + same prompt = repeatable workflow |
| **Free** | No per-token cost for a full engagement |

## Human-in-the-Loop

The workflow enforces a strict validation gate at every phase:

1. **Ground every prompt** in real tool output (Nmap XML, BloodHound JSON, Burp requests, jadx code) — never ask the AI to invent.
2. **Require citations** — the model must reference the exact data it used and answer `UNKNOWN` when unsure.
3. **Never execute blindly** — every AI-generated script/command runs first in the lab.
4. **Log everything** — each AI claim is recorded in a validation log with a pass/fail verdict.

See [`docs/04-VALIDATION-FRAMEWORK.md`](docs/04-VALIDATION-FRAMEWORK.md).

---

## Repository Structure

```
AI-Assisted-VAPT-Automation-Reporting-Workflow/
|-- README.md
|-- docs/
|    |-- 00-PROJECT-PLAN.md            # Master plan — 4 weeks + fast-track schedule
|    |-- 01-LAB-SETUP-GUIDE.md         # AI lab + vulnerable lab environment setup
|    |-- 02-PROMPT-LIBRARY.md          # Prompt template standard + testing log
|    |-- 03-PRIVACY-ETHICS-CHECKLIST.md# Mandatory rules before any test
|    `-- 04-VALIDATION-FRAMEWORK.md    # Anti-hallucination & accuracy review SOP
|-- prompts/                          # 23 versioned prompt templates (5 phases)
|    |-- recon/                        # R1–R4
|    |-- active-directory/             # AD1–AD5
|    |-- web/                          # W1–W5
|    |-- mobile/                       # M1–M4
|    `-- reporting/                    # RP1–RP5
|-- scripts/
|    |-- vapt_ai.py                    # Local-only Ollama runner + --cross-check
|    |-- run_benchmarks.py             # 6-task x 2-model benchmark runner
|    |-- run_dvwa_pocs.py              # Live DVWA PoC & screenshot automation
|    |-- ingest/                       # Nmap XML, enum, BloodHound (+BFS), Burp, jadx
|    |-- generated/                    # Validated AI-generated PS1, Python, Frida JS
|    `-- reporting/                    # calc_cvss.py, diff_draft.py, PDF/DOCX/PPTX builders
|-- deliverables/                     # Final evaluated Week 2–4 reports, SOP & slides
|-- templates/                        # Report & validation-log skeletons
|-- lab/                              # Benchmark results & isolated AD lab dataset
|-- evidence/                         # Raw scans, captures & validation log (gitignored)
`-- reports/                          # Built docs & scratch outputs (gitignored)
```

## Deliverables & Measured Highlights

| Deliverable | Path | Highlights |
|---|---|---|
| **Week 1 Benchmarks** | [`lab/model-benchmarks.md`](lab/model-benchmarks.md) | `qwen2.5:3b` (69.3 tok/s, 5.0/5) vs `llama3.2:3b` (39.3 tok/s, 4.3/5) on RTX 3050 Ti |
| **Week 2 AD & Recon** | [`deliverables/week2-ad-recon-analysis.md`](deliverables/week2-ad-recon-analysis.md) | Real Kali Nmap + BloodHound BFS Ground Truth + 4 validated audit scripts |
| **Week 3 Web & Mobile** | [`deliverables/week3-web-mobile-analysis.md`](deliverables/week3-web-mobile-analysis.md) | 5 live DVWA PoCs with screenshots + `jadx` DIVA review + 2 Frida scripts |
| **Week 4 AI Draft vs Final** | [`deliverables/VAPT-Report-Human-Edited.pdf`](deliverables/VAPT-Report-Human-Edited.pdf) | 9 findings verified via `calc_cvss.py`; `diff_draft.py` (10.3% word similarity) |
| **Hallucination Audit** | [`deliverables/week4-hallucination-check-and-diff.md`](deliverables/week4-hallucination-check-and-diff.md) | Full Week 1–4 accuracy & caught hallucinations summary |
| **Reusable SOP** | [`deliverables/REUSABLE-VAPT-AI-SOP.pdf`](deliverables/REUSABLE-VAPT-AI-SOP.pdf) | End-to-end repeatable workflow SOP |
| **Presentation** | [`deliverables/DEPI-Project5-Presentation.pptx`](deliverables/DEPI-Project5-Presentation.pptx) | 12-slide defense deck with measured benchmark chart & demo script |

## Documentation Map

| Doc | Purpose |
|---|---|
| [00-PROJECT-PLAN](docs/00-PROJECT-PLAN.md) | Full day-by-day plan (4 weeks) + 12-day fast track |
| [01-LAB-SETUP-GUIDE](docs/01-LAB-SETUP-GUIDE.md) | Install Ollama/LM Studio/GPT4All, models, benchmarks, lab VMs |
| [02-PROMPT-LIBRARY](docs/02-PROMPT-LIBRARY.md) | Prompt format standard + starter templates per phase |
| [03-PRIVACY-ETHICS-CHECKLIST](docs/03-PRIVACY-ETHICS-CHECKLIST.md) | Must-pass checklist before testing |
| [04-VALIDATION-FRAMEWORK](docs/04-VALIDATION-FRAMEWORK.md) | How we validate AI output & measure hallucination rate |

## Weekly Deliverables

| Week | Theme | Deliverables |
|---|---|---|
| 1 | AI Lab Setup & Prompt Engineering | AI lab setup guide, local model benchmarks, prompt library, privacy/ethics checklist |
| 2 | AI for Recon & Active Directory Analysis | AI-assisted AD analysis, generated scripts, validation notes, hallucination/accuracy review |
| 3 | AI for Web & Mobile Analysis | AI-assisted web/mobile findings, payload suggestions, code explanations, validated PoCs |
| 4 | AI-Assisted Reporting & Quality Assurance | Final AI-assisted VAPT report, human-edited report, hallucination check, reusable workflow/SOP, presentation |

## Quickstart

```bash
# 1. Start local Ollama & verify Llama + Qwen models
ollama list   # llama3.2:3b and qwen2.5:3b

# 2. Run 6-task local benchmark matrix
python scripts/run_benchmarks.py

# 3. Ingest Nmap XML -> grounded LLM context -> dual-model cross-check
python scripts/ingest/nmap_to_context.py evidence/week2/nmap-lab.xml --out evidence/week2/nmap_context.txt
python scripts/vapt_ai.py --template R1 --var-file nmap_xml_summary=evidence/week2/nmap_context.txt --cross-check

# 4. Verify CVSS 3.1 math & render final report
python scripts/reporting/calc_cvss.py "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
python scripts/reporting/build_vapt_report.py deliverables/vapt-report-human-edited.md \
  --pdf deliverables/VAPT-Report-Human-Edited.pdf --docx deliverables/VAPT-Report-Human-Edited.docx \
  --title "VAPT Assessment Report — Human-Edited Final"
```

## Ethics & Legal Notice

This project is an **educational deliverable** for the DEPI graduation program.
All testing is performed **only** against self-owned, isolated lab machines
(DVWA, OWASP Juice Shop, Metasploitable, intentionally-vulnerable AD labs, DIVA/InsecureBankv2 Android apps).

- No third-party system is ever targeted.
- The privacy/ethics checklist in [`docs/03-PRIVACY-ETHICS-CHECKLIST.md`](docs/03-PRIVACY-ETHICS-CHECKLIST.md) is mandatory and must pass before any test.
- Any real engagement would require explicit written authorization.

## License

MIT — see [LICENSE](LICENSE).
