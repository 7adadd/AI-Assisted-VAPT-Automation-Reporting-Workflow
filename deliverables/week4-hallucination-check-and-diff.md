# AI Draft vs. Human-Edited Report — Deterministic Diff Metrics

| Metric | Value |
|---|---|
| AI Draft length | 398 lines / 3050 words |
| Human-Edited length | 190 lines / 2208 words |
| Word-level similarity | 10.3% |
| Line-level similarity | 18.4% |
| Words purely inserted | 40 |
| Words purely deleted | 339 |
| Words replaced (AI -> Human) | 2439 -> 1896 |

## Unified Diff Excerpt
```diff
--- vapt-report-ai-draft.md
+++ vapt-report-human-edited.md
@@ -1,398 +1,190 @@
-# VAPT Assessment Report — Unedited Local AI Draft (Week 4)
+# Vulnerability Assessment & Penetration Testing (VAPT) Report — Human-Edited Final
 
-> **Status:** RAW AI DRAFT (prior to Human L4 QA & `calc_cvss.py` verification). Generated directly from validated lab notes using `qwen2.5:3b` (`RP1`, `RP4`) and `llama3.2:3b` (`RP3`).
+**Engagement:** DEPI Graduation Program — Project 5 Isolated Lab Assessment  
+**Targets:** `LAB.LOCAL` Active Directory Dataset · Live DVWA (`172.24.186.6/dvwa`) · `diva-beta.apk` (`jakhar.aseem.diva`)  
+**Lead Analyst:** Mohamed Reda Elhaddad (`@7adadd`)  
+**Assessment Date:** 2026-11-26 · **Classification:** Educational — Isolated Self-Owned Lab Only
 
-## 1. Executive Summary (AI Draft — `llama3.2:3b`)
+---
 
-**Executive Summary: Security Posture and Business Risks**
+## 1. Executive Summary
 
-**Summary of Findings**
+An AI-assisted, human-validated Vulnerability Assessment and Penetration Testing (VAPT) engagement was conducted against a controlled three-tier laboratory environment comprising an Active Directory domain graph (`LAB.LOCAL`), a live Damn Vulnerable Web Application (`DVWA` on Kali WSL2 Apache/PHP/MariaDB), and a decompiled Android mobile application (`DIVA`). Across all targets, **9 distinct findings** were confirmed through manual verification and live exploitation: **1 Critical**, **4 High**, and **4 Medium** severity issues.
 
-Our engagement revealed a comprehensive set of security vulnerabilities across the LAB.LOCAL environment, including Active Directory, Live DVWA Web App, and DIVA Android APK. The findings are summarized below, highlighting the top 3 business risks and immediate strategic recommendations.
+### Risk Distribution Summary (Verified via `calc_cvss.py`)
 
-**Top 3 Business Risks**
+| Severity | CVSS v3.1 Range | Count | Finding IDs |
+|---|---|---|---|
+| **Critical** | 9.0 – 10.0 | **1** | `F-02` (9.8) |
+| **High** | 7.0 – 8.9 | **4** | `F-01` (8.8), `F-04` (8.8), `F-05` (8.8), `F-03` (7.1) |
+| **Medium** | 4.0 – 6.9 | **4** | `F-06` (6.5), `F-08` (6.2), `F-07` (5.4), `F-09` (5.1) |
+| **Low** | 0.1 – 3.9 | **0** | — |
+| **Total** | — | **9** | **100% Human-Validated** |
 
-1. **Insufficient Password Security**: The presence of cleartext passwords in Active Directory ([F-03]) and weak password policies ([F-03]) poses a significant risk to the organization. This vulnerability could be exploited by attackers to gain unauthorized access to sensitive data.
-2. **SQL Injection in DVWA**: The UNION-based SQL injection vulnerability in the DVWA User Lookup feature ([F-04]) allows attackers to execute arbitrary SQL commands, potentially compromising sensitive data.
-3. **Cleartext Credentials in DIVA APK**: The hardcoded vendor secret and cleartext credit card logging in the DIVA APK ([F-08]) provide a direct path for attackers to access sensitive financial information.
+### Top 3 Business Risks
+1. **Unauthenticated Domain Takeover via AS-REP Roasting & DCSync (`F-02`, CVSS 9.8 Critical):** An unauthenticated attacker can crack `j.smith`'s AS-REP hash (`DONT_REQ_PREAUTH`), reset `svc-sync`'s password (`ForceChangePassword`), and replicate all domain password hashes via `DCSync`.
+2. **Full Database & Server Compromise on Web Tier (`F-04`, `F-05`, CVSS 8.8 High):** Live exploitation of UNION-based SQL Injection (`F-04`) extracted all user MD5 credentials, while OS Command Injection (`F-05`) yielded arbitrary command execution as `www-data`.
+3. **Multi-Hop AD ACL Escalation & Cleartext Service Secrets (`F-01`, `F-03`, `F-08`):** Delegated `GenericAll`/`WriteDacl` rights grant `m.ali` a 3-hop path to `Domain Admins`, compounded by a cleartext password in AD (`TempPass2026!`) and hardcoded/logged mobile secrets.
 
-**Immediate Strategic Recommendations**
+### AI-Assistance & Human-Validation Disclosure (Ethics Rule E7)
+In accordance with the project Privacy & Ethics Policy, initial triage, attack-path explanations, payload brainstorming, and draft finding prose were accelerated using **100% locally hosted LLMs** (`qwen2.5:3b` and `llama3.2:3b` via Ollama on `127.0.0.1:11434`). **No lab or test data was sent to any cloud API.** Every finding, payload, line citation, and CVSS v3.1 score in this final report was independently verified by the human analyst (`L1–L4` gates), resulting in the removal of several AI hallucinations present in the raw draft (documented in `week4-hallucination-check-and-diff.md`).
 
-1. Implement a robust password policy, including password rotation and complexity requirements.
-2. Conduct a thorough review of the DVWA Web App and implement a secure coding practice to prevent SQL injection vulnerabilities.
-3. Update the DIVA APK to remove hardcoded vendor secrets and implement secure credit card logging practices.
+---
 
-**AI-Assistance and Human-Validation Disclosure**
+## 2. Scope & Methodology
 
-Our engagement utilized AI-assistance tools to identify vulnerabilities, but all findings were manually validated by our team to ensure accuracy and relevance. We recommend that the organization consider implementing AI-assistance tools to support their security posture, while also maintaining human validation to ensure the accuracy and relevance of findings.
+- **Active Directory & Recon (`Week 2`):** Real Kali WSL Nmap XML (`nmap -sV -sC`) + service banner enumeration + BloodHound JSON (`LAB.LOCAL`) solved deterministically via BFS (`scripts/ingest/bloodhound_to_context.py`).
+- **Web Application (`Week 3`):** Live DVWA (`low` security level) hosted on Apache 2.4.68 / PHP 8.4.22 / MariaDB 11.8.8; 5 live PoCs executed and screenshotted via Playwright (`scripts/run_dvwa_pocs.py`).
+- **Mobile Application (`Week 3`):** `diva-beta.apk` decompiled via `jadx` v1.5.6 (`718` classes); static source & manifest analysis plus static/signature-verified Frida hooks.
+- **CVSS v3.1 Verification (`Week 4`):** All Base Scores computed deterministically with `scripts/reporting/calc_cvss.py`.
 
-**Risk Distribution Summary**
+---
 
-| Risk Type | Count | Severity |
-| --- | --- | --- |
-| High | 4 | CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H |
-| Medium | 3 | CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:N |
-| Low | 1 | CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N |
+## 3. Summary of Validated Findings
 
-Note: The risk distribution summary is based on the CVSS severity scores and the number of findings for each risk type.
+| ID | Title | Domain | CVSS v3.1 Vector | Score | Severity | Validation |
+|---|---|---|---|---|---|---|
+| `F-01` | Multi-Hop AD Privilege Escalation (`GenericAll` -> `WriteDacl`) | AD | `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H` | **8.8** | **High** | ✅ L1+L3+L4 |
+| `F-02` | AS-REP Roasting + `ForceChangePassword` -> `DCSync` | AD | `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` | **9.8** | **Critical** | ✅ L1+L3+L4 |
+| `F-03` | Cleartext Password in AD Description, Weak Policy & R/W Share | AD | `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:N` | **7.1** | **High** | ✅ L1+L4 |
+| `F-04` | SQL Injection (UNION-Based) in DVWA User Lookup | Web | `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H` | **8.8** | **High** | ✅ L2 (Live PoC) |
+| `F-05` | OS Command Injection in DVWA Ping Utility | Web | `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H` | **8.8** | **High** | ✅ L2 (Live PoC) |
+| `F-06` | Local File Inclusion (Path Traversal) in DVWA File Inclusion | Web | `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N` | **6.5** | **Medium** | ✅ L2 (Live PoC) |
+| `F-07` | Reflected & Stored Cross-Site Scripting (XSS) in DVWA | Web | `CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N` | **5.4** | **Medium** | ✅ L2 (Live PoC) |
+| `F-08` | Hardcoded Vendor Secret & Cleartext Credit Card Logging | Mobile | `CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N` | **6.2** | **Medium** | ✅ L1+L4 |
+| `F-09` | Plaintext SharedPreferences, Debuggable Flag & Exported Provider | Mobile | `CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N` | **5.1** | **Medium** | ✅ L1+L4 |
 
-## 2. Scope & Summary Table
+---
 
-| ID | Title | Proposed CVSS Vector |
-|---|---|---|
-| F-01 | Active Directory Multi-Hop Privilege Escalation via GenericAll and WriteDacl | CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H |
-| F-02 | AS-REP Roasting Chained with ForceChangePassword Leading to DCSync | CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H |
-| F-03 | Cleartext Password in AD Description, Weak Password Policy & Writable Share | CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:N |
-| F-04 | SQL Injection (UNION-Based) in DVWA User Lookup | CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H |
-| F-05 | OS Command Injection in DVWA Ping Utility | CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H |
-| F-06 | Local File Inclusion (Path Traversal) in DVWA File Inclusion Module | CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N |
-| F-07 | Reflected and Stored Cross-Site Scripting (XSS) in DVWA | CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N |
-| F-08 | Hardcoded Vendor Secret & Cleartext Credit Card Logging in DIVA APK | CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N |
-| F-09 | Plaintext SharedPreferences, Debuggable Flag & Exported ContentProvider in DIVA APK | CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N |
-
-## 3. Detailed Technical Findings (AI Draft — `qwen2.5:3b`)
+## 4. Detailed Technical Findings
 
 ### F-01: Active Directory Multi-Hop Privilege Escalation via GenericAll and WriteDacl
+- **Severity:** **High** — **CVSS 8.8** (`CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H`)
+- **Affected Asset:** `LAB.LOCAL` (`m.ali@LAB.LOCAL`, `svc-backup@LAB.LOCAL`, `IT-ADMINS@LAB.LOCAL`, `DOMAIN ADMINS@LAB.LOCAL`)
+- **Description:** A 3-hop ACL escalation path exists in `LAB.LOCAL`. Low-privileged user `m.ali` holds `GenericAll` over `svc-backup` (which also exposes a Kerberoastable SPN `MSSQLSvc/db01.lab.local:1433`). `svc-backup` is a member of `IT-ADMINS`, which holds `WriteDacl` directly on `DOMAIN ADMINS`.
+- **Steps to Reproduce (Verified via BFS & ACL Audit):**
+  1. Run `python scripts/ingest/bloodhound_to_context.py lab/ad-lab-dataset/bloodhound_lab.json` to confirm shortest path `[E01] -> [E02] -> [E03]`.
+  2. Verify dangerous ACEs in `lab/ad-lab-dataset/acl_dump.txt` lines `[1]` and `[2]` (and via `scripts/generated/ad_acl_audit.ps1`).
+  3. Abuse `GenericAll` (targeted Kerberoasting / Shadow Credentials / password reset) on `svc-backup`, inherit `IT-ADMINS` membership, and leverage `WriteDacl` on `DOMAIN ADMINS` to add a controlled account.
+- **Impact:** Complete compromise of Domain Admins and full Active Directory domain control.
+- **Remediation:** Revoke `GenericAll` for `m.ali` on `svc-backup`, remove `WriteDacl` granted to `IT-ADMINS` on `DOMAIN ADMINS`, and rotate `svc-backup`'s password to a 25+ character random secret (or migrate to gMSA).
 
-```markdown
-## Title & Finding ID
-Finding-1: BloodHound Privilege Escalation
-
-## Severity & CVSS v3.1 Vector
-CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H
-
-## Affected Asset / Component
-- Domain: LAB.LOCAL
-- Vulnerability: Privilege Escalation via BloodHound
-
-## Description
-The BloodHound tool has been used to identify a privilege escalation vulnerability. User `m.ali@LAB.LOCAL` has the `GenericAll` permission on the `svc-backup` service account, which is also Kerberoastable. Additionally, the `svc-backup` service account is a member of the `IT-ADMINS` group, which has the `WriteDacl` permission on the `DOMAIN ADMINS` security group. This allows for potential escalation of privileges.
-
-## Steps to Reproduce
-1. Use the BloodHound tool to connect to the `LAB.LOCAL` domain.
-2. Identify the `m.ali@LAB.LOCAL` user with the `GenericAll` permission on the `svc-backup` service account.
-3. Identify the `svc-backup` service account as a member of the `IT-ADMINS` group.
-4. Verify the `IT-ADMINS` group has the `WriteDacl` permission on the `DOMAIN ADMINS` security group.
-5. Use the identified information to escalate privileges.
```


---

## Human QA Audit — Categorized Corrections (AI Draft -> Human-Edited Final)

| Finding / Section | Category | Raw AI Draft Error / Hallucination | Human QA Correction Applied |
|---|---|---|---|
| **Executive Summary (`RP3`)** | Factual / Count Error | Listed `High: 4, Medium: 3, Low: 1` (8 findings, missing 1, wrong severity labels) | Rebuilt exact verified table (`Critical: 1, High: 4, Medium: 4 = 9`) via `calc_cvss.py` |
| **`F-01` & `F-02` (AD)** | CVSS Scope & Script Hallucination | `F-01` used `S:C` (9.9); `F-02` labeled `High` despite `10.0` vector, repeated fake `GetSystemUser()` PowerShell 3×, truncated mid-sentence | Set `S:U` (`8.8 High` for `F-01`, `9.8 Critical` for `F-02`); added real `bloodhound_to_context.py` & Impacket steps |
| **`F-03` (AD Hygiene)** | Major Hallucination Removed | Misread user `helpdesk01` as `"helpdesk01 server"` with RDP and invented `Set-ItemProperty Winlogon DefaultPassword` registry command | Corrected to AD `description` attribute enumeration (`enum4linux_lab.txt`) and policy/share verification |
| **`F-06` (DVWA LFI)** | Major Hallucination + Broken Output | Claimed `/etc/passwd` *"contains root's password"* and emitted truncated `%252f...` URL | Corrected fact (`/etc/shadow` stores hashes; `/etc/passwd` exposes accounts) and fixed exact PoC URL + `poc-05-lfi.png` |
| **`F-07` & `F-09` (Severity)** | CVSS Severity Mismatch | Labeled `F-07` (`5.4`) and `F-09` (`5.1`) as **High** | Corrected both to **Medium** per `calc_cvss.py` |
| **`F-08` (Mobile Logcat)** | Dangerous Remediation Removed | Advised replacing `Log.e(...)` with `Log.w(...)` (still leaks credit cards to Logcat!) and invented `jadx -f` flag | Replaced with complete removal of sensitive PII/CC logging from all `Log.*` calls |
| **`RP4` Roadmap** | Priority Error | Placed `F-04` (SQLi `8.8`) and `F-05` (CMDi `8.8`) in Short-Term (30d) instead of Immediate (0–7d) | Re-ordered horizons strictly by verified CVSS severity (`F-02, F-01, F-04, F-05` Immediate) |

---

## Compiled Cross-Phase Hallucination & Accuracy Review (Weeks 1–4)

| Week / Phase | Items / Claims Checked | Strictly Verified (✅) | Partially Correct (⚠️) | Hallucinated / Rejected (❌) | Key Failure Pattern Caught |
|---|---|---|---|---|---|
| **Week 1 (6×2 Benchmarks)** | 12 | 11 (`91.7%` >=4/5) | 1 (`8.3%`) | 0 (`0%`) | `llama3.2:3b` dropped SQLi rewrite detail on T4 |
| **Week 2 (Recon & AD)** | 12 | 6 (`50.0%`) | 3 (`25.0%`) | 3 (`25.0%`) | Port/account swaps (`Llama`), extra BFS edge (`Qwen AD1`), XML/JSON schema guesses (`AD3`) |
| **Week 3 (Web & Mobile)** | 12 | 7 (`58.3%`) | 2 (`16.7%`) | 3 (`25.0%`) | Unexecuted HTML-comment XSS (`Llama`), fake Android SSL class names (`Qwen M2`) |
| **Week 4 (AI Draft Findings)** | 9 findings | 3 (`33.3%`) | 4 (`44.4%`) | 2 major (`22.2%`) | Wrong CVSS severity labels, `/etc/passwd` password myth, `helpdesk01` server hallucination |

**Key Conclusion:** Local 3B models (`qwen2.5:3b` and `llama3.2:3b`) cut triage and first-drafting time drastically while keeping 100% of sensitive data offline, **but human-in-the-loop gates (`L1–L4`), deterministic parsers (`nmap_to_context.py`, BFS BloodHound solver, `calc_cvss.py`), and live PoC validation are non-negotiable** to eliminate the ~22–25% hallucination/error rate before report delivery.
