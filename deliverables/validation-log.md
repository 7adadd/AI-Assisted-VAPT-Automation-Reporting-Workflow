# Validation Log — Weeks 2 & 3 (Anti-Hallucination Audit)

> **Principle:** An AI claim is not a finding. Every AI output used passes L1 (Data-verified), L2 (Lab-executed), L3 (Cross-model), and L4 (Human QA).

## Week 2 — Recon & Active Directory (12 Evaluated Claims)

| ID | Phase / Template | AI Claim / Output Summary | Model | Source Cited | Ground Truth Check | Result | Verdict |
|---|---|---|---|---|---|---|---|
| W2-01 | Recon `R1` | Open ports `80/tcp` Apache2, `3306/tcp` mysql, `8888/tcp` Werkzeug; closed `22, 443, 445, 8080` | `qwen2.5:3b` | `[nmap:port 80/tcp]`, `[nmap:port 3306/tcp]`, `[nmap:port 8888/tcp]` | Checked against `evidence/week2/nmap-lab.xml` | 100% port & service match | ✅ L1+L3 |
| W2-02 | Recon `R2` | Extracted Apache `2.4.68`, PHP `8.4.22`, MariaDB `11.8.8`; misread PHP `Expires: 2009` anti-cache header as broken expiration | `llama3.2:3b` | `[enum:line 1..25]` | Checked `curl -i` headers in `enum-lab.txt` | Versions exact; header interpretation wrong | ⚠️ Partial |
| W2-03 | Recon `R1` | Listed `Werkzeug httpd 3.1.9` under `80/tcp` and claimed Apache default page is "vulnerable to exploitation" | `llama3.2:3b` | `[nmap:port 8888/tcp]` | `nmap-lab.xml` shows Werkzeug on `8888/tcp`, Apache default page only | Port mixup + false-positive overclaim | ❌ Hallucination |
| W2-04 | AD `AD1` | Path 1: `m.ali --(GenericAll)--> svc-backup --(MemberOf)--> IT-Admins --(WriteDacl)--> Domain Admins` | `qwen2.5:3b` | `[bh:edge E01]`, `[bh:edge E02]`, `[bh:edge E03]` | Verified against `bloodhound_ground_truth.json` BFS output | Exact 3-hop match | ✅ L1+L3 |
| W2-05 | AD `AD1` | Path 2 extended with `E02: svc-sync --(MemberOf)--> IT-Admins` | `qwen2.5:3b` | `[bh:edge E02]` | `bloodhound_lab.json` shows `E02` belongs to `svc-backup`, not `svc-sync`; `svc-sync` ends at `LAB.LOCAL` (DCSync) | Fabricated edge link on Path 2 | ❌ Hallucination |
| W2-06 | AD `AD2` | Filtered `acl_dump.txt` to exact 5 dangerous ACEs (`GenericAll`, `WriteDacl`, `ForceChangePassword`, `GetChangesAll`, `GetChanges`), excluding benign `[6]`/`[7]` | `qwen2.5:3b` | `[acl:1..5]` | Verified line-by-line against `lab/ad-lab-dataset/acl_dump.txt` | 5/5 dangerous ACEs exact | ✅ L1+L3 |
| W2-07 | AD `AD5` | Claimed `j.smith` is Kerberoasting target, `IT-Admins` group is AS-REP Roasting target, and invented `klist /me` & `klist /user:` | `llama3.2:3b` | `[SPN LIST]`, `[AS-REP LIST]` | Swapped accounts/attacks vs `spn_asrep_dump.txt`; invalid Windows `klist` flags | Account swap + fake flags | ❌ Hallucination |
| W2-08 | AD `AD4` | Extracted all 7 users (including `helpdesk01` `TempPass2026!`), 3 groups, 6 shares (`DeptDocs` R/W), and password policy (`min=7`, `lockout=0`) | `qwen2.5:3b` | `[enum:line 1..10]` | Verified against `enum4linux_lab.txt` | Extraction accurate | ✅ L1 |
| W2-09 | AD `AD5` | Correctly tagged `j.smith` as AS-REP Roasting (`DONT_REQ_PREAUTH`), omitted `svc-backup` from priority table, suggested `klist -s` | `qwen2.5:3b` | `[asrep:j.smith 2]` | Checked `spn_asrep_dump.txt` and `klist` CLI syntax | Core class right, incomplete table + invalid flag | ⚠️ Partial |
| W2-10 | AD `AD3` | Generated `nmap_triage_verifier.py` and `bh_path_auditor.py` | `qwen2.5:3b` | `AD3` Python output | Executed in Python against lab XML/JSON | Needed XML `<state>`/`<address>` & JSON schema key fixes (then passed 0 errors) | ⚠️ Partial -> ✅ L2 |
| W2-11 | AD `AD3` | Generated `ad_spn_audit.ps1` using read-only `Get-ADUser -Filter {Enabled -eq $true -and ServicePrincipalName -ne $null}` | `qwen2.5:3b` | `AD3` PS output | PowerShell AST parser check | 0 syntax errors, read-only cmdlets valid | ✅ L2 (AST) |
| W2-12 | AD `AD2` | Identified all 5 dangerous ACEs in `acl_dump.txt` (`m.ali`, `IT-Admins`, `j.smith`, `svc-sync` x2) | `llama3.2:3b` | `[acl:line 1..5]` | Checked `acl_dump.txt` (noisy `GenericRead` row added, core 5 right) | Core ACEs verified | ✅ L1+L3 |

### Week 2 Accuracy Summary
- **Total claims evaluated:** 12
- **Verified (✅):** 6 (**50.0%**)
- **Partially correct (⚠️):** 3 (**25.0%**)
- **Hallucinations / Rejected (❌):** 3 (**25.0%**)

---

## Week 3 — Web (DVWA) & Mobile (DIVA) (12 Evaluated Claims)

| ID | Phase / Template | AI Claim / Output Summary | Model | Source Cited | Ground Truth Check | Result | Verdict |
|---|---|---|---|---|---|---|---|
| W3-01 | Web `W1` | Identified `id` SQLi parameter, `PHPSESSID` session cookie, and UNION SELECT SQLi hypothesis at `[http:line 96]` | `qwen2.5:3b` | `[http:line 96]` | Verified against `01-sqli-request.txt` & live DVWA PoC (`poc-01-sqli.png`) | Parameter & SQLi confirmed live | ✅ L1+L2+L3 |
| W3-02 | Web `W2` | Suggested `<script>alert('XSS-R')</script>`, `<svg onload=alert('XSS-R')/>`, `<img src=x onerror=alert('XSS-R')>` under 50-char limit | `qwen2.5:3b` | `name` parameter | Executed against live DVWA `xss_r` (`poc-02-xss-reflected.png`) | Alert dialog `'XSS-R'` fired in Playwright | ✅ L2 |
| W3-03 | Web `W2` | Suggested HTML comment payload `<!-- <script>...</script> -->` and invented non-existent `username` parameter | `llama3.2:3b` | `[http:line 98]` | Tested HTML comment in DOM (does not execute) + checked DVWA `xss_r` form | Non-executing payload + invented param | ❌ Hallucination |
| W3-04 | Web `W5` | Approved `<script>alert('XSS-R')</script>` and `127.0.0.1; id`; rejected `1'; DROP TABLE users;-- -` as destructive | `llama3.2:3b` | Payloads #2, #3, #5 | Reviewed payload syntax & non-destructive lab policy | Correct safety triage on those 3 | ✅ L1 |
| W3-05 | Web `W3` | Extracted `Server: Apache/2.4.68 (Debian)` `[http:line 15]`, unencoded `ip` input `[http:line 110]`, missing `Content-Security-Policy` & `X-Frame-Options` | `llama3.2:3b` | `[http:line 15]`, `[http:line 110]` | Checked `04-cmdi-request.txt` headers & HTML form | Verified in raw HTTP response | ✅ L1 |
| W3-06 | Web `W5` | Marked read-only `UNION SELECT` and `../../../../etc/passwd` as `UNKNOWN / REJECT` | `qwen2.5:3b` | Payloads #1, #4 | Verified read-only behavior on live DVWA (`poc-01`, `poc-05`) | Overly conservative false reject | ⚠️ Partial |
| W3-07 | Mobile `M1` | Found hardcoded `"vendorsecretkey"` at `HardcodeActivity.java:19`, CC logcat leak at `LogActivity.java:23`, plaintext SharedPreferences at `InsecureDataStorage1Activity.java:20` | `llama3.2:3b` | `[jadx:HardcodeActivity.java:19]`, `[jadx:LogActivity.java:23]`, `[jadx:InsecureDataStorage1Activity.java:20]` | Verified exact line numbers in `evidence/week3/diva-src/` | All 3 vulnerabilities & lines exact | ✅ L1 |
| W3-08 | Mobile `M1` | `llama3.2:3b` misclassified `new RuntimeException()` (`LogActivity.java:31`) as "Critical Weak cryptography"; `qwen2.5:3b` returned false-negative `UNKNOWN` on 4-class bundle | Both | `[jadx:LogActivity.java:31]` | Inspected `LogActivity.java` & `HardcodeActivity.java` | False-positive Critical + false-negative refusal | ❌ Hallucination |
| W3-09 | Mobile `M3` | Flagged `android:debuggable="true"`, `android:allowBackup="true"`, and reported `usesCleartextTraffic` as `NOT SPECIFIED IN SNIPPET` | `qwen2.5:3b` | `[manifest:19..20]` | Checked `AndroidManifest.xml` lines 18–19 | Core flags exact (off by 1 line on tag) | ✅ L1+L3 |
| W3-10 | Mobile `M2` / `M3` | `M2` SSL script hallucinated `SSLCertificateSocketFactory$TrustManager.onGetCertificateChain` & `OkHttp$CertificatePinner.pinToKeyStore`; `M3` hallucinated `permission.CUSTOM` | `qwen2.5:3b` | Generic SSL / `[manifest:60]` | Checked Android AOSP / OkHttp3 APIs and `AndroidManifest.xml` | Fake Java class/method & manifest names | ❌ Hallucination |
| W3-11 | Mobile `M2` | Generated Frida hook for `jakhar.aseem.diva.HardcodeActivity.access` and `LogActivity.processCC` from `HardcodeActivity.java` context | `qwen2.5:3b` | `HardcodeActivity.java` | Checked V8 JS syntax + verified signatures in `diva-src/` | Signatures matched; cleaned `this.access(view)` call | ✅ L1+L2 (static) |
| W3-12 | Mobile `M4` | Correctly replied `UNKNOWN - insufficient data` when given a one-line summary without `<DATA>` code | `qwen2.5:3b` | Prompt `M4` | Grounding rule #3 enforcement test | Honest refusal instead of guessing | ⚠️ Partial (safe refusal) |

### Week 3 Accuracy Summary
- **Total claims evaluated:** 12
- **Verified (✅):** 7 (**58.3%**)
- **Partially correct (⚠️):** 2 (**16.7%**)
- **Hallucinations / Rejected (❌):** 3 (**25.0%**)

---

## Interactive GUI Validation Log

| ID | Phase / Template | AI Claim / Output Summary | Model | Source Cited | Ground Truth Check | Result | Verdict |
|---|---|---|---|---|---|---|---|
