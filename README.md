# AI-Assisted VAPT Automation & Reporting Workflow

**DEPI Graduation Program — Project 5**

A privacy-first, human-in-the-loop workflow that uses **locally-hosted LLMs** (Ollama / LM Studio / GPT4All) to assist every phase of a Vulnerability Assessment & Penetration Testing (VAPT) engagement — from reconnaissance and Active Directory analysis to web/mobile testing and professional report writing.

> **Core principle:** AI accelerates the analyst — it never replaces human validation.
> Every AI output (attack paths, payloads, scripts, report text) is **verified manually in an isolated lab** before it is trusted.

---

## Why local models?

| Benefit | Meaning |
|---|---|
| **Local inference** | Prompt data sent to Ollama is restricted to the configured loopback endpoint. |
| **Network scope** | PortSwigger import/inspection requires outbound HTTPS; the optional solver actively sends bounded requests only to the exact authorized lab instance after consent. This is not an air-gapped/offline mode. |
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
|-- prompts/                          # 24 versioned prompt templates (5 phases)
|    |-- recon/                        # R1–R4
|    |-- active-directory/             # AD1–AD5
|    |-- web/                          # W1–W5 + PS1 PortSwigger lab analyst
|    |-- mobile/                       # M1–M4
|    `-- reporting/                    # RP1–RP5
|-- scripts/
|    |-- vapt_ai.py                    # Local-only Ollama runner + --cross-check
|    |-- safe_lab_http.py              # Scope-pinned HTTPS-only lab transport (host/redirect/request caps)
|    |-- lab_inspect.py                # Single-URL passive lab surface inspector
|    |-- port_solver.py                # Official-signal solve verification + secret redaction
|    |-- agentic_solver.py             # Evidence-driven Observe→Reason→Act→Verify loop
|    |-- evaluate_challenges.py        # 12-challenge DVWA/PortSwigger passive suite runner
|    |-- run_benchmarks.py             # 6-task x 2-model benchmark runner
|    |-- run_dvwa_pocs.py              # Live DVWA PoC & screenshot automation
|    |-- ingest/                       # Nmap XML, enum, BloodHound (+BFS), Burp, jadx
|    |-- generated/                    # Validated AI-generated PS1, Python, Frida JS
|    `-- reporting/                    # calc_cvss.py, diff_draft.py, PDF/DOCX/PPTX builders
|-- deliverables/                     # Final evaluated Week 2–4 reports, SOP & slides
|-- app/                              # Localhost-only FastAPI Web GUI (127.0.0.1:8000)
|-- run_gui.py                        # One-command GUI launcher
|-- tests/                            # API smoke tests & Playwright UI checks
|-- templates/                        # Report & validation-log skeletons
|-- lab/                              # Benchmarks, AD dataset & DVWA/PortSwigger samples
|-- evidence/                         # Raw scans, captures & validation log (gitignored)
`-- reports/                          # Built docs & scratch outputs (gitignored)
```

## Deliverables & Measured Highlights

| Deliverable | Path | Highlights |
|---|---|---|
| **Week 1 Benchmarks** | [`lab/model-benchmarks.md`](lab/model-benchmarks.md) | Recorded local runs; see task-level methodology and limitations in the file |
| **Week 2 AD & Recon** | [`deliverables/week2-ad-recon-analysis.md`](deliverables/week2-ad-recon-analysis.md) | Includes collected recon artifacts and a documented synthetic AD graph/BFS validation path |
| **Week 3 Web & Mobile** | [`deliverables/week3-web-mobile-analysis.md`](deliverables/week3-web-mobile-analysis.md) | DVWA test artifacts and static DIVA review; Frida code validation is not equivalent to on-device execution |
| **Week 4 AI Draft vs Final** | [`deliverables/VAPT-Report-Human-Edited.pdf`](deliverables/VAPT-Report-Human-Edited.pdf) | Human-edited report; CVSS vectors are re-computed by `calc_cvss.py` |
| **Hallucination Audit** | [`deliverables/week4-hallucination-check-and-diff.md`](deliverables/week4-hallucination-check-and-diff.md) | Recorded validation outcomes; challenge evaluator signals are heuristic unless explicitly human-adjudicated |
| **Reusable SOP** | [`deliverables/REUSABLE-VAPT-AI-SOP.pdf`](deliverables/REUSABLE-VAPT-AI-SOP.pdf) | End-to-end repeatable workflow SOP |
| **Presentation** | [`deliverables/DEPI-Project5-Presentation.pptx`](deliverables/DEPI-Project5-Presentation.pptx) | 15-slide defense deck covering Weeks 1–4, AegisVAPT GUI, 12-challenge suite & Port Solver |
| **AegisVAPT Workbench** | [`run_gui.py`](run_gui.py) | Localhost-only analyzer / Port Solver / dashboard / graph / report GUI with session-token hardening |
| **Challenge Suite Eval** | [`deliverables/challenge-evaluation-results.md`](deliverables/challenge-evaluation-results.md) | 12/12 passive diagnoses across DVWA + PortSwigger patterns |
| **Defense & Walkthrough Guide** | [`deliverables/PROJECT-WALKTHROUGH-AND-DEFENSE-GUIDE.pdf`](deliverables/PROJECT-WALKTHROUGH-AND-DEFENSE-GUIDE.pdf) | Complete Arabic walkthrough of Weeks 1–4, post-plan additions, live demo script & 12 Q&A cards |

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

```powershell
# 1. Create a virtual environment and install dependencies
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Confirm local Ollama and models
ollama list   # expected: llama3.2:3b and qwen2.5:3b

# 3. Run deterministic offline tests (no Ollama or network)
python -I -m unittest discover -s tests -p "test_solver_unit.py" -v
python -I -m unittest discover -s tests -p "test_gui_api.py" -v

# 4. Start the localhost AegisVAPT GUI in this terminal
python -I run_gui.py
```

The launcher prints a one-run session token. Open `http://127.0.0.1:8000` in that same local browser session; POST requests from the GUI use the injected token. For API smoke tests, use the GUI session or a local test client; do not expose the server to a LAN.

Optional integrations: `tests/test_gui_api_live.py` requires `VAPT_RUN_LIVE_TESTS=1`, a running local Ollama, and outbound HTTPS. It is not part of the default offline test suite.

For a scan/review workflow, use artifacts you captured from your own lab:

```powershell
python -I scripts/ingest/nmap_to_context.py <your-nmap.xml> --out <context.txt>
python -I scripts/vapt_ai.py --template R1 --var-file nmap_xml_summary=<context.txt>
python -I scripts/reporting/calc_cvss.py "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
```

## Web GUI Studio (`run_gui.py`)

A FastAPI dashboard bound to `127.0.0.1:8000`. Static UI assets are bundled locally. Local Ollama inference uses loopback; PortSwigger import and the explicitly consented Port Solver require outbound HTTPS to the selected training instance. The solver is active, bounded, and must not be used outside an instance the operator is authorized to test:

1. **Analyzer:** Upload or paste Nmap XML, enum output, BloodHound JSON, HTTP captures, or decompiled mobile source; select a grounded prompt and local model.
2. **Port Solver:** Optional active interaction with the caller's own Academy instance. Passive observation is the default; enabling state changes requires an explicit checkbox. The UI reports official completion separately from attempts and suggestions.
3. **Dashboard:** Ollama/model availability, validation metrics, benchmark charts, and the bundled 12-item artifact suite.
4. **AD Attack Paths:** Cytoscape graph with computed layout and highlighted BFS edges when the graph fixture is available.
5. **Reports & Export:** CVSS calculation, AI-draft vs human-edited diff, PoC image gallery, and report/SOP/presentation exports.

## Ethics & Legal Notice

This project is an **educational deliverable** for the DEPI graduation program.
All testing is performed **only** against self-owned, isolated lab machines
(DVWA, OWASP Juice Shop, Metasploitable, intentionally-vulnerable AD labs, DIVA/InsecureBankv2 Android apps).

- No unrelated third-party system is targeted. The optional PortSwigger Solver is limited to an Academy training instance explicitly opened/authorized by the user and requires consent before state-changing requests.
- Local inference uses loopback; importing/inspecting a PortSwigger URL makes external HTTPS requests to that host, so the project is not fully offline.
- The privacy/ethics checklist in [`docs/03-PRIVACY-ETHICS-CHECKLIST.md`](docs/03-PRIVACY-ETHICS-CHECKLIST.md) is mandatory and must pass before any test.
- Any real engagement would require explicit written authorization.

## License

No license file is currently included. Do not redistribute or reuse this repository until the owner selects and adds a license.
