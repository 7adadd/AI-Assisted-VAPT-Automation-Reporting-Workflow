# 00 — Master Project Plan
## AI-Assisted VAPT Automation & Reporting Workflow (DEPI — Project 5)

> **Status:** ACTIVE · **Owner:** [@7adadd](https://github.com/7adadd) · **Duration:** 4 weeks official / **12-day fast track available**
> **Last updated:** 2026-11-22

---

## 1. Project Identity

| Field | Value |
|---|---|
| Project | AI-Assisted VAPT Automation & Reporting Workflow |
| Program | DEPI Graduation Program — Project 5 |
| Repo | https://github.com/7adadd/AI-Assisted-VAPT-Automation-Reporting-Workflow |
| Official schedule | 4 weeks (Week 1 → Week 4 as per program sheet) |
| Fast-track schedule | 12 working days (parallel streams, section 8) |
| Environment | Windows 11 host + isolated lab VMs (host-only network) |

### Objective
Build a **repeatable, privacy-first workflow** where locally-hosted LLMs assist every VAPT phase — recon, Active Directory analysis, web & mobile testing, and report writing — with a mandatory **human-in-the-loop validation gate** and measurable hallucination/accuracy tracking.

### Non-Goals (explicit)
- ❌ No autonomous exploitation. AI suggests; the human decides and executes.
- ❌ No cloud LLM APIs with test data. Local models only.
- ❌ No testing of systems we don't own or aren't authorized for.
- ❌ Not building a product — building a **workflow + SOP** that is reusable.

---

## 2. Success Criteria (measurable)

| # | Criterion | Target |
|---|---|---|
| S1 | Local AI lab operational | Ollama + LM Studio + GPT4All installed; ≥3 models benchmarked |
| S2 | Prompt library | ≥20 tested templates across 5 phases |
| S3 | AD phase | AI correctly explains ≥2 BloodHound attack paths, verified against GUI ground truth |
| S4 | AD scripts | ≥3 AI-generated scripts that run successfully in the lab |
| S5 | Web phase | ≥5 AI-suggested payloads validated with PoC evidence in DVWA/Juice Shop |
| S6 | Mobile phase | ≥2 AI-generated Frida scripts working in the emulator |
| S7 | Reporting | Full report generated (AI draft) + human-edited version + tracked diff |
| S8 | Validation | Validation log covers **100%** of AI claims used; accuracy rate computed |
| S9 | SOP | Reusable workflow SOP that a new team member could follow unaided |
| S10 | Presentation | Final deck + live demo |

---

## 3. Architecture — 5 Layers

```
+------------------------------------------------------------+
|  L5  REPORTING PIPELINE                                    |
|      Markdown findings -> pandoc -> DOCX/PDF, CVSS 3.1     |
+------------------------------------------------------------+
|  L4  VALIDATION LAYER  (human-in-the-loop)                 |
|      validation log, ground-truth compare, accuracy %      |
+------------------------------------------------------------+
|  L3  PROMPT LIBRARY (versioned templates + variables)      |
+------------------------------------------------------------+
|  L2  INGEST ADAPTERS (tool -> structured LLM context)      |
|      nmap XML, enum4linux-ng, BloodHound JSON              |
|      Burp requests, jadx source, Frida output              |
+------------------------------------------------------------+
|  L1  AI RUNTIME (local)                                    |
|      Ollama (primary), LM Studio, GPT4All                  |
|      llama3.1, qwen2.5, deepseek-coder                     |
+------------------------------------------------------------+
```

**Data flow:** Tool output (L2 ingest) → filled prompt template (L3) → local model (L1) → AI output → validation gate (L4) → either *"validated finding"* feeding L5, or *"rejected/hallucinated"* logged and re-prompted.

---

## 4. Tech Stack & Hardware

### Hardware — measured on the project machine (2026-11-22)
| Spec | Value |
|---|---|
| CPU | AMD Ryzen 5 5600H |
| RAM | 16 GB |
| GPU | NVIDIA RTX 3050 Ti Laptop (4 GB VRAM) — CUDA active in Ollama ✅ |
| Disk free | C: **31 GB** · D: 1.1 GB → **WSL low-disk lab chosen — zero VMs** |
| Ollama | v0.40.2, Windows native, verified working |

### Model inventory & adequacy (measured 2026-11-22)
Installed: `llama3.2:3b` (main assistant, Q4_K_M, 128K ctx) · `llama-guard3:1b` (safety classifier — used by the red-teaming project, not ours) · `sentinel-lockdown` / `sentinel-bank` (custom llama3.2:3b variants — **belong to the primary AI-red-teaming graduation project; kept untouched**).

Measured on RTX 3050 Ti: prompt eval **625 tok/s**, generation **31.5 tok/s** — fast and usable (first row in `lab/model-benchmarks.md`).

| Phase | llama3.2:3b verdict |
|---|---|
| W1 prompt testing & triage prompts | ✅ sufficient |
| W2 recon triage | ✅ sufficient (validated in live test) |
| W2 AD attack paths + script generation | ⚠️ elevated hallucination risk — add **qwen2.5:7b** |
| W3 web payload suggestions | ✅ acceptable with the validation gate |
| W3 mobile code review + Frida scripts | ❌ too weak — needs qwen2.5:7b |
| W4 report drafting | ⚠️ acceptable; 7B output is markedly better |

**Decision:** keep `llama3.2:3b` as the fast/draft model + download **`qwen2.5:7b`** as the primary model — a single 4.7 GB download that fits the 31 GB free. Optional only if space allows: `deepseek-coder:6.7b` (3.8 GB). LM Studio / GPT4All are **optional** (the program sheet says "Ollama, LM Studio, **or** GPT4All") — skip them to save disk.

### Software stack
| Layer | Tools |
|---|---|
| AI runtime | **Ollama** (primary, CLI + localhost:11434 API), **LM Studio** (GUI + OpenAI-compatible server :1234), **GPT4All** (GUI, LocalDocs) |
| Models | `llama3.1:8b-instruct-q4_K_M`, `qwen2.5:7b-instruct-q4_K_M`, `deepseek-coder:6.7b-instruct`, optional `qwen2.5:14b` |
| Recon/AD | Nmap, enum4linux-ng, smbclient, ldapdomaindump (inside kali WSL), **BloodHound + Neo4j (Windows) + bloodhound-python collector** |
| Web | **Burp Suite Community** (Windows), DVWA (apache2 + php + mariadb inside kali WSL), Juice Shop optional |
| Mobile | jadx (Windows, static), **Frida + frida-tools**, DIVA / InsecureBankv2 — runtime tests on a **physical Android phone via USB** (no emulator — disk constraint); static-only fallback if no phone |
| AD target | **Samba AD DC inside kali WSL** (replaces the Windows Server VM), intentionally-weak config (Kerberoastable SPN, AS-REP roastable user, writable ACLs) |
| Reporting | Python 3.12, **pandoc** (+ reference.docx), markdown report template, cvss calculator cross-check |
| Automation | Python (xml.etree for Nmap, `ollama` pip package for scripted prompting) |

---

## 5. Repository Structure

See [`../README.md`](../README.md#repository-structure) — the skeleton already exists locally with all folders created.

---

## 6. Detailed 4-Week Plan (day by day)

> Legend: 🛠 = you (installs/VMs/running tools) · 🤖 = AI agent can generate instantly · ✅ = checkpoint/deliverable

### Week 1 — AI Lab Setup & Prompt Engineering (Days 1–7)

| Day | Tasks | Who | Output |
|---|---|---|---|
| D1 | ✅ **Done** — Ollama v0.40.2 already installed; server-start issue diagnosed & fixed; llama3.2:3b verified working on GPU | 🛠 | ✅ |
| D2 | ✅ **Done (minimal)** — Ollama alone satisfies the program sheet ("Ollama, LM Studio, **or** GPT4All"). LM Studio/GPT4All optional, skipped to save disk | 🛠 | Primary runtime ready |
| D3 | **Benchmark matrix**: 6 fixed tasks per model. ✅ First row measured (llama3.2:3b: 31.5 tok/s gen / 625 tok/s prompt on RTX 3050 Ti). Complete the matrix for `qwen2.5:7b` after pull | 🛠 (+ script I provide) | `lab/model-benchmarks.md` |
| D4 | kali-linux WSL ✅ already installed — install attacker toolset via apt (nmap, enum4linux-ng, impacket, smbclient, seclists); enable WSL→Windows Ollama API access (mirrored networking); checkpoint WSL | 🛠 | Attacker workspace ready |
| D5 | Provision **Samba AD DC inside kali WSL** + apply weak-AD config (2 Kerberoastable SPNs, 1 AS-REP roastable user, writable ACL path, password in description field); checkpoint distro | 🛠 | AD lab ready |
| D6 | Define **prompt template standard** (7-field format, see doc 02) + write first batch: recon templates ×4, AD templates ×5, report templates ×4 | 🤖→🛠 review | `prompts/` v0.1 |
| D7 | Write **privacy & ethics rules** + **lab setup guide**; test every template on real lab data once; commit Week 1 | 🤖 + 🛠 | ✅ Week 1 deliverables: setup guide, benchmarks, prompt library, ethics checklist |

**Week 1 checkpoint:** you can ask a local model a grounded question about your own lab scan and get a cited, correct answer.

### Week 2 — AI for Recon & Active Directory Analysis (Days 8–14)

| Day | Tasks | Who | Output |
|---|---|---|---|
| D8 | Nmap full scan of lab (XML output: `-sV -O -oA`); enum4linux-ng + smbclient + ldapdomaindump against the DC; save all raw outputs to `evidence/week2/` | 🛠 | Raw recon data |
| D9 | Build **ingest script** `scripts/ingest/nmap_to_context.py` (Nmap XML → clean structured text) + same for enum4linux output | 🤖 | Reusable ingest layer |
| D10 | BloodHound + Neo4j (Windows); collect from kali WSL with **bloodhound-python** against Samba AD; import; screenshot ground-truth attack paths | 🛠 | BloodHound ground truth |
| D11 | **Attack-path prompts**: feed BloodHound edges → ask AI to explain the Kerberoast path & AS-REP path step-by-step; compare answer to GUI ground truth; log verdicts | 🛠 | `evidence/week2/attack-path-analysis.md` |
| D12 | **Permission analysis prompts**: ACL/GPO anomalies; ask AI for a PowerShell script to list writeable objects / abused permissions; run it in lab | 🛠 | ≥3 working AI scripts |
| D13 | **Hallucination/accuracy review**: fill validation log for every Week-2 AI claim; compute accuracy %; cross-check critical claims with a 2nd model | 🛠 | ✅ validation notes |
| D14 | Compile "AI-assisted AD analysis" doc (findings + which claims were AI-correct vs hallucinated); commit Week 2 | 🤖 + 🛠 | ✅ Week 2 deliverables |

**Week 2 checkpoint:** every AI attack-path claim is either verified against BloodHound/actual execution, or logged as hallucinated.

### Week 3 — AI for Web & Mobile Analysis (Days 15–21)

| Day | Tasks | Who | Output |
|---|---|---|---|
| D15 | Deploy DVWA inside kali WSL (apache2 + php + mariadb via apt — ~1 GB, no docker needed); point Burp proxy at it; baseline crawl | 🛠 | Web targets ready |
| D16 | **Burp request prompts**: paste real captured requests → AI explains parameters, identifies vulnerability class, suggests payloads (with citations to the request) | 🛠 | `evidence/week3/web-analysis.md` |
| D17 | **Payload validation**: test AI-suggested payloads in DVWA (SQLi, XSS, command injection, SSRF); capture PoC screenshots; reject/log the ones that fail | 🛠 | ≥5 validated PoCs |
| D18 | Mobile: decompile **DIVA** + **InsecureBankv2** with **jadx** (Windows, static — works with zero extra disk); runtime Frida tests on a **physical Android phone via USB** (Frida gadget if not rooted) — static-only fallback if no phone | 🛠 | Decompiled code ready |
| D19 | **Code-review prompts**: feed decompiled classes → AI finds hardcoded creds, insecure crypto, exported components; explain each finding's impact | 🛠 | Code explanations |
| D20 | **Frida prompts**: AI generates SSL-pinning-bypass & root-detection-bypass scripts; run via `frida-tools` in emulator; iterate until working | 🛠 | ≥2 working Frida scripts |
| D21 | Compile AI-assisted web/mobile findings + code explanations; update validation log; commit Week 3 | 🤖 + 🛠 | ✅ Week 3 deliverables |

**Week 3 checkpoint:** every payload/PoC in evidence has a screenshot or tool output proving it ran — no AI-only claims.

### Week 4 — AI-Assisted Reporting & Quality Assurance (Days 22–28)

| Day | Tasks | Who | Output |
|---|---|---|---|
| D22 | Build **report template** (exec summary, scope, methodology, findings, CVSS, remediation, appendices) in Markdown + pandoc `reference.docx` | 🤖 | `templates/report-template.md` |
| D23 | **Finding-writing prompts**: feed each validated Week-2/3 finding → AI drafts finding text + CVSS 3.1 vector; verify every score against a manual CVSS calculator | 🛠 | `reports/ai-draft-v1.md` |
| D24 | AI drafts **executive summary + remediation** sections; review for overclaiming/understating severity | 🛠 | Full AI draft complete |
| D25 | **Human edit pass**: produce the human-edited report; generate a tracked **diff AI-draft vs human** (word-level) → shows exactly where AI was wrong/weak | 🤖 script | ✅ both reports + diff |
| D26 | Build **reporting pipeline** `scripts/reporting/build_report.py` (pandoc md→docx/pdf) + write the **reusable SOP** covering the whole workflow end-to-end | 🤖 + 🛠 | One-command report build |
| D27 | **Final QA**: hallucination check table finalized, accuracy % computed, peer review, CVSS cross-check | 🛠 | ✅ QA record |
| D28 | **Presentation**: slides (problem → workflow → demo → results → lessons) + live demo script; final commit + push | 🤖 + 🛠 | ✅ Week 4 deliverables |

---

## 7. Deliverables Checklist (mapped to the program sheet)

- [x] **Week 1:** AI lab setup guide · local model benchmarks (`llama3.2:3b` + `qwen2.5:3b` × 6 tasks) · 23-template prompt library (`prompts/`) · privacy/ethics checklist
- [x] **Week 2:** AI-assisted AD & recon analysis (`deliverables/week2-ad-recon-analysis.md`) · 4 generated scripts (`scripts/generated/`) · validation notes (`evidence/validation-log.md`) · hallucination/accuracy review
- [x] **Week 3:** AI-assisted web/mobile findings (`deliverables/week3-web-mobile-analysis.md`) · payload suggestions · `jadx` DIVA code explanations · 5 live DVWA validated PoCs + 2 verified Frida scripts
- [x] **Week 4:** Final AI-assisted VAPT report (`VAPT-Report-AI-Draft.pdf`) · human-edited report (`VAPT-Report-Human-Edited.pdf/.docx`) · hallucination check & diff (`week4-hallucination-check-and-diff.md`) · reusable SOP (`REUSABLE-VAPT-AI-SOP.pdf`) · presentation (`DEPI-Project5-Presentation.pptx`)

---

## 8. Fast-Track Schedule — 12 working days 🚀

For finishing "في أسرع وقت". Two parallel streams: **AI/tooling** (mostly my instant generation + your review) and **lab/execution** (your machine time). They interleave.

| Day | Stream A — AI/Docs/Scripts 🤖 | Stream B — Lab Execution 🛠 |
|---|---|---|
| 1 | All Week-1 docs already generated (done in this session) | ✅ Ollama verified working; llama3.2:3b confirmed |
| 2 | Benchmark script ready | Pull `qwen2.5:7b` (4.7 GB); kali WSL toolset via apt |
| 3 | Prompt library v0.2 (all 20+ templates) | Run benchmark matrix (30–45 min) |
| 4 | Nmap/enum ingest scripts | Samba AD DC up in WSL + weak-AD config |
| 5 | Weak-AD config script (PowerShell) + validation log template | BloodHound install; Nmap + enum4linux scans of DC |
| 6 | AD analysis doc skeleton | Attack-path prompts vs BloodHound; run AI PS scripts |
| 7 | — | Validation review Week-2 → accuracy % |
| 8 | Web analysis doc skeleton | DVWA + Juice Shop + Burp; payload tests Day A |
| 9 | Mobile analysis doc skeleton | jadx + Frida script tests |
| 10 | Report template + CVSS assistant + pipeline script | Feed validated findings → AI draft report |
| 11 | Diff script + SOP document | Human edit pass + final QA |
| 12 | Presentation deck generation | Demo dry-run; **commit + push final** |

**Critical path:** Ollama install (D1) → benchmark (D3) → BloodHound data (D5) → validated findings (D7) → report (D10–11).
**Day 12 is buffer** — anything that slips lands there.

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Weak hardware → slow models | High | q4 quantized 7–8B models; 3B fallback; run benchmarks before committing to a model |
| Model hallucination on AD paths | High | Ground-truth compare vs BloodHound GUI; 2-model cross-check; validation log mandatory |
| Disk nearly full (31 GB free) | High | **WSL low-disk lab chosen — zero VMs**: Samba AD + DVWA inside kali WSL (~3–4 GB), models capped at ~9 GB (3b kept + one 7B); monitor WSL vhdx growth; `wsl --shutdown` after heavy sessions |
| Burp Community limits | Low | DVWA/Juice Shop are simple targets; Community is enough |
| Frida/emulator version mismatch | Medium | Pin emulator image + `frida-server` version together; document exact versions |
| Time slip | Medium | Fast-track has buffer day; deliverables are incremental commits |
| Accidental real-data leak | Critical | gitignore evidence/reports; ethics checklist gate; local-only models |

---

## 10. Division of labor — fastest possible execution

**What the AI agent (me) generates instantly, same session:**
- All documentation & guides (done ✅)
- Prompt templates for all 5 phases
- Python ingest scripts (Nmap XML, enum4linux, BloodHound JSON → context)
- Weak-AD configuration PowerShell script
- Benchmark runner script
- Report template + pandoc pipeline + diff tool
- Presentation deck draft

**What requires your machine/hands (unavoidable):**
- ✅ Done: Ollama installed & fixed; llama3.2:3b benchmarked (31.5 tok/s gen on GPU)
- Pull `qwen2.5:7b` — the single remaining model download (4.7 GB)
- Install kali-WSL toolset; provision Samba AD DC + weak config
- Run scans, bloodhound-python collection, Burp, Frida tests (phone via USB, or static fallback)
- Capturing PoC screenshots and evidence

**Rule of thumb:** you never wait on me; I never wait on you except for validation results, which feed the next doc.

---

## 11. Definition of Done per week

| Week | Done means |
|---|---|
| 1 | `ollama run` works ✅; 2 models benchmarked (llama3.2:3b + qwen2.5:7b); ≥13 templates tested once; docs committed |
| 2 | Validation log full for Week 2; accuracy % computed; ≥3 AI scripts executed in lab |
| 3 | ≥5 validated web PoCs + ≥2 working Frida scripts, all with evidence |
| 4 | Both reports + diff exist; SOP written; QA done; presentation ready; repo pushed |
