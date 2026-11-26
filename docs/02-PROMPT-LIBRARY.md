# 02 — Prompt Library (Standard + Starter Templates)

The prompt library is a **Week-1 deliverable** and the heart of the workflow.
Templates live in `prompts/<phase>/` as versioned Markdown files; this document defines the standard and ships the starter set (target: **≥20 templates** by end of Week 1).

---

## 1. Template standard (7 fields)

Every template file must follow this structure:

```
# PROMPT-ID — Short name
## Phase            recon | active-directory | web | mobile | reporting
## Role             (system-style role framing)
## Variables        {{list of placeholders}}
## Anti-hallucination rules   (embedded in every prompt)
## Template         (the actual prompt text)
## Expected output format     (exact structure)
## Validation hook  (how a human verifies this output)
## Tested with      model / runtime / date / result
```

### Universal anti-hallucination block (embedded in every template)

```
GROUNDING RULES (mandatory):
1. Use ONLY the data provided between <DATA> tags. Do not use outside knowledge.
2. Cite the exact evidence for every claim, e.g. [nmap:port 445], [bloodhound-edge], [jadx:MainActivity.java:42].
3. If the data does not support an answer, reply exactly: UNKNOWN - insufficient data, and say what data you would need.
4. Never invent hosts, usernames, versions, ports, CVEs or scores.
5. Distinguish clearly between: FACT (in data) / INFERENCE (reasoned from data) / UNKNOWN.
```

---

## 2. Starter templates by phase

> On execution (Week 1 D6) each template below is split into its own file in `prompts/<phase>/`. They are shown here for review.

### 2.1 Recon (`prompts/recon/`)

**R1 — Nmap scan triage**
- *Variables:* `{{nmap_xml_summary}}`
- *Task:* "Summarize the following Nmap scan of the lab target: open ports, services+versions, notable misconfigurations. Order findings by attack-surface relevance. Output: table (port/service/version/observation) + ranked next-steps (top 5) with the evidence for each."
- *Validation hook:* re-open the XML; confirm every listed port/version matches.

**R2 — Service deep-dive**
- *Variables:* `{{service_banner_block}}`
- *Task:* "For this service banner, list: known risky default settings visible in the banner, relevant hardening checklist, and lab-safe tests to confirm misconfiguration. Mark each item FACT/INFERENCE per the grounding rules."

**R3 — Enumeration next-steps planner**
- *Variables:* `{{all_recon_outputs}}`
- *Task:* "Given all recon outputs for the host, produce a prioritized enumeration plan (max 10 commands) with the reason for each. Do not include exploitation commands."

**R4 — Recon report section**
- *Variables:* `{{recon_findings_json}}`
- *Task:* "Turn these structured recon findings into a 'Reconnaissance Summary' report section in professional English, ≤300 words, with a table."

### 2.2 Active Directory (`prompts/active-directory/`)

**AD1 — BloodHound attack-path explainer**
- *Variables:* `{{bloodhound_edges_json}}`, `{{target_user}}`
- *Task:* "Explain every shortest attack path from `{{target_user}}` to Domain Admin based ONLY on the provided edges. For each hop: edge type → what it means → prerequisite → the exact abuse technique name. Cite each edge."
- *Validation hook:* compare step-by-step with the BloodHound GUI path; any invented edge = logged hallucination.

**AD2 — Permission/ACL anomaly analyzer**
- *Variables:* `{{acl_dump}}`
- *Task:* "List ACL entries in this dump that grant dangerous rights (GenericAll, WriteDacl, WriteOwner, GetChangesAll, ForceChangePassword, etc.), who grants to whom, and why each is exploitable."

**AD3 — Script generator (safe enumeration)**
- *Variables:* `{{objective}}`, `{{domain}}`
- *Task:* "Write a PowerShell script for: `{{objective}}` in domain `{{domain}}`. Requirements: read-only (no changes), no exploitation, commented, uses built-in AD module or PowerView. Output script + expected sample output."
- *Validation hook:* **read the script line-by-line before running**; run in lab only.

**AD4 — enum4linux triage**
- *Variables:* `{{enum4linux_output}}`
- *Task:* "Extract from this enum4linux-ng output: users, groups, shares, password-policy highlights, and anything anomalous. Flag items worth deeper testing."

**AD5 — Kerberoast/AS-REP target checklist**
- *Variables:* `{{spn_list}}`, `{{asrep_list}}`
- *Task:* "Given these SPN and AS-REP listings, produce a target-priority table and the lab-safe verification commands for each target."

### 2.3 Web (`prompts/web/`)

**W1 — Burp request explainer**
- *Variables:* `{{http_request}}`
- *Task:* "Explain this captured request: each parameter's apparent role, authentication mechanism visible in headers, and 3 candidate vulnerability classes with the reasoning. Cite exact header/param lines."

**W2 — Payload suggester**
- *Variables:* `{{request_context}}`, `{{vuln_class}}`, `{{constraints}}`
- *Task:* "Suggest 5 payloads for `{{vuln_class}}` given this request context. Constraints: `{{constraints}}` (e.g., length limit, must be URL-safe). For each: payload, why it might work here specifically, and the lab test to confirm."
- *Validation hook:* test in DVWA/Juice Shop; capture screenshot; failed ones are logged, not silently dropped.

**W3 — Response analysis**
- *Variables:* `{{http_response}}`
- *Task:* "Analyze this response for: error disclosure, version leaks, reflected content, stack traces. Cite lines."

**W4 — PoC write-up**
- *Variables:* `{{validated_poc_notes}}`
- *Task:* "Turn these validated PoC notes into a finding write-up: Steps to reproduce (exact requests), impact, evidence references. Facts only from notes."

**W5 — Payload safety review (mobile/web shared)**
- *Task:* "Review the following payloads for a lab test: confirm each is non-destructive, reversible, and confined to the lab target. Flag anything that could cause data loss or persistence."

### 2.4 Mobile (`prompts/mobile/`)

**M1 — Decompiled code reviewer**
- *Variables:* `{{java_source_block}}`, `{{class_purpose}}`
- *Task:* "Review this decompiled class for: hardcoded credentials/secrets, weak crypto (MD5, ECB, static keys), insecure logging, exported components, certificate-validation flaws. Cite exact line numbers."

**M2 — Frida script generator**
- *Variables:* `{{bypass_goal}}`, `{{app_package}}`
- *Task:* "Generate a Frida script for `{{bypass_goal}}` (e.g., SSL pinning bypass) against app `{{app_package}}`. Use well-known stable APIs (Java.use, OkHttp CertificatePatcher pattern). Output: script + hook rationale + how to verify it attached."
- *Validation hook:* run in emulator; confirm `frida -U -l script.js` hooks fire.

**M3 — Manifest analyzer**
- *Variables:* `{{android_manifest_xml}}`
- *Task:* "Analyze this AndroidManifest: exported components with no permission, `allowBackup`, `debuggable`, cleartext traffic, deep links. Rank by risk."

**M4 — Vulnerability confirmation plan**
- *Variables:* `{{suspected_issue}}`
- *Task:* "Propose the minimal lab steps to confirm `{{suspected_issue}}` on the DIVA/InsecureBankv2 app, including the exact interaction to capture as evidence."

### 2.5 Reporting (`prompts/reporting/`)

**RP1 — Finding writer**
- *Variables:* `{{validated_finding_notes}}`, `{{cvss_vector}}`
- *Task:* "Write a professional finding: Title, CVSS 3.1 `{{cvss_vector}}`, Description, Impact, Steps to reproduce (from notes only), Remediation (specific + prioritized). Do not add claims absent from the notes."

**RP2 — CVSS 3.1 assistant**
- *Variables:* `{{finding_summary}}`
- *Task:* "Propose a CVSS v3.1 vector for this finding with a one-line justification per metric. Then list what must be manually verified before the score is accepted."
- *Validation hook:* **recompute score in an official calculator**; discrepancy = fix the vector.

**RP3 — Executive summary**
- *Variables:* `{{all_findings_table}}`, `{{engagement_context}}`
- *Task:* "Write a ≤1-page executive summary for a non-technical audience: posture, top 3 risks in business terms, prioritized recommendations. No tool names except where essential."

**RP4 — Remediation plan**
- *Variables:* `{{findings_with_cvss}}`
- *Task:* "Produce a remediation roadmap: immediate (0–7d), short (30d), strategic (90d), mapped to finding IDs, ordered by CVSS and business impact."

**RP5 — Draft-vs-human diff report**
- *Task (meta, no LLM):* generated by script `scripts/reporting/diff_draft.py` — word-level diff of the AI draft and the human-edited report, summarized into: corrections of fact, style edits, hallucinations removed.

---

## 3. Testing log (per template, Week 1–4 Execution)

| Template | Model(s) | Runtime | Date | Result | Notes |
|---|---|---|---|---|---|
| `R1`–`R3` | `qwen2.5:3b`, `llama3.2:3b` | Ollama | 2026-11-26 | ✅ Tested (`Qwen` 100% port match; `Llama` 80/8888 swap caught) | Verified vs `evidence/week2/nmap-lab.xml` |
| `R4` | `llama3.2:3b`, `qwen2.5:3b` | Ollama | 2026-11-26 | ✅ Tested via `run_benchmarks.py` (T1/T4) | `qwen2.5:3b` scored 5/5 |
| `AD1`, `AD2`, `AD4`, `AD5` | `qwen2.5:3b`, `llama3.2:3b` | Ollama | 2026-11-26 | ✅ Tested (`AD2` 5/5 ACEs; `AD1`/`AD5` hallucinations logged) | Verified vs `bloodhound_ground_truth.json` |
| `AD3` | `qwen2.5:3b` | Ollama | 2026-11-26 | ✅ Tested (4 scripts generated -> L2 QA fixed & executed) | `scripts/generated/*.ps1, *.py` |
| `W1`–`W5` | `qwen2.5:3b`, `llama3.2:3b` | Ollama | 2026-11-26 | ✅ Tested on live DVWA HTTP captures + 5 live PoCs | `poc-01`..`poc-05` screenshots captured |
| `M1`–`M4` | `qwen2.5:3b`, `llama3.2:3b` | Ollama | 2026-11-26 | ✅ Tested on `jadx`-decompiled `diva-beta.apk` | 2 Frida scripts syntax/signature-verified |
| `RP1`–`RP5` | `qwen2.5:3b`, `llama3.2:3b` + Python | Ollama | 2026-11-26 | ✅ Tested on 9 findings + `calc_cvss.py` + `diff_draft.py` | 10.3% word similarity after QA |
