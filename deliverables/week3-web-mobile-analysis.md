# Week 3 Deliverable — AI-Assisted Web & Mobile Analysis

**Web Target:** Live DVWA (`http://172.24.186.6/dvwa/`, Apache 2.4.68 + PHP 8.4.22 + MariaDB 11.8.8 in Kali WSL2)  
**Mobile Target:** `diva-beta.apk` (`jakhar.aseem.diva`), decompiled via `jadx` v1.5.6 (`718` classes)  
**Author:** Mohamed Reda Elhaddad (`@7adadd`) · **Date:** 2026-11-26

---

## 1. Web Application Testing (DVWA — 5 Validated Live PoCs)

All 5 HTTP request/response pairs were captured from live DVWA (`scripts/run_dvwa_pocs.py`), formatted into `[http:line N]` context via `scripts/ingest/burp_to_context.py`, analyzed with prompts `W1`, `W2`, `W3`, and `W5`, and executed in headless Chromium via Playwright to verify real exploitation.

| # | Vulnerability Class | Endpoint & Parameter | Validated Payload | Live Proof Observed | Screenshot |
|---|---|---|---|---|---|
| 1 | **SQL Injection (UNION)** | `/dvwa/vulnerabilities/sqli/` (`id`) | `1' UNION SELECT user,password FROM users-- -` | Extracted 5 user accounts + MD5 password hashes (`admin`, `gordonb`, `1337`, `pablo`, `smithy`) | [poc-01-sqli.png](assets/poc-01-sqli.png) |
| 2 | **Reflected XSS** | `/dvwa/vulnerabilities/xss_r/` (`name`) | `<script>alert('XSS-R')</script>` | Playwright captured live JS alert dialog `'XSS-R'` | [poc-02-xss-reflected.png](assets/poc-02-xss-reflected.png) |
| 3 | **Stored XSS** | `/dvwa/vulnerabilities/xss_s/` (`mtxMessage`) | `<script>alert('XSS-S')</script>` | Persisted in MariaDB guestbook; alert `'XSS-S'` fired on page reload | [poc-03-xss-stored.png](assets/poc-03-xss-stored.png) |
| 4 | **OS Command Injection** | `/dvwa/vulnerabilities/exec/` (`ip`) | `127.0.0.1; id` | Executed `id` in Kali WSL shell: `uid=33(www-data) gid=33(www-data)` | [poc-04-cmdi.png](assets/poc-04-cmdi.png) |
| 5 | **Local File Inclusion (LFI)** | `/dvwa/vulnerabilities/fi/` (`page`) | `../../../../../../etc/passwd` | Dumped `/etc/passwd` starting with `root:x:0:0:root:/root:/bin/bash` | [poc-05-lfi.png](assets/poc-05-lfi.png) |

### 1.1 Payload Suggestion & Safety Gate Observations (`W2` & `W5`)
- **Succeeded AI Payloads (`W2`, `qwen2.5:3b`):** `<script>alert('XSS-R')</script>`, `<svg onload=alert('XSS-R')/>`, and `<img src=x onerror=alert('XSS-R')>` all satisfied the 50-character limit and execute in `low` security mode.
- **Rejected / Failed AI Payloads (`W2`, `llama3.2:3b`):**
  - `%3C!--%3Cscript%3Ealert%28%27XSS-R%27%29%3C%2Fscript%3E--%3E` — **failed execution** because HTML comment delimiters prevent script evaluation.
  - `<script>alert('XSS-R')</script> + <input type="text" name="username">` — **rejected** for exceeding the 50-char constraint and inventing a non-existent `username` parameter.
- **Safety Review (`W5`):** `llama3.2:3b` properly flagged `1'; DROP TABLE users;-- -` as destructive (`REJECT`), while both models over-conservatively marked read-only `UNION SELECT` and `LFI` as `REJECT`, requiring human override before lab testing.

---

## 2. Mobile Application Static Analysis (`diva-beta.apk` via `jadx`)

### 2.1 Verified Findings in Decompiled Java & Manifest (`M1` & `M3`)

| Finding | Source File & Line Citation | Observed Vulnerable Code / Configuration | AI Detection Notes (`Llama` vs `Qwen`) |
|---|---|---|---|
| **Hardcoded Vendor Secret** | `HardcodeActivity.java:19` | `if (hckey.getText().toString().equals("vendorsecretkey"))` | `llama3.2:3b` cited exact line `19`; `qwen2.5:3b` gave false-negative `UNKNOWN` on bundled 4-class input |
| **Sensitive Credit Card Logging** | `LogActivity.java:23` | `Log.e("diva-log", "Error while processing transaction with credit card: " + cctxt.getText().toString());` | `llama3.2:3b` cited exact line `23`; also falsely flagged `new RuntimeException()` (`line 31`) as "Critical Weak cryptography" |
| **Plaintext SharedPreferences** | `InsecureDataStorage1Activity.java:20–26` | `PreferenceManager.getDefaultSharedPreferences(this)` stores `"user"` and `"password"` in cleartext XML | `llama3.2:3b` cited line `20` accurately |
| **Debuggable & Backup Enabled** | `AndroidManifest.xml:18–19` | `android:debuggable="true"` and `android:allowBackup="true"` | Both models caught both flags (`qwen` off by 1 line; `llama` exact lines 18–19) |
| **Exported Content Provider & Implicit Intents** | `AndroidManifest.xml:57–80` | `NotesProvider` (`android:exported="true"`) + `APICredsActivity`/`APICreds2Activity` `<intent-filter>` without `android:permission` | `qwen2.5:3b` hallucinated `permission.CUSTOM`; human review verified `NotesProvider` |

---

## 3. Frida Scripts Generated & Validation (`M2`)

Two Frida scripts were generated via `M2` (`qwen2.5:3b`) and validated statically:

1. **`scripts/generated/frida_diva_hardcode_hook.js`**
   - Hooks `jakhar.aseem.diva.HardcodeActivity.access(android.view.View)` and `jakhar.aseem.diva.LogActivity.processCC(java.lang.String)`.
   - **Validation:** V8 JavaScript syntax check passed (0 errors), and class/method signatures were verified verbatim against `evidence/week3/diva-src/sources/jakhar/aseem/diva/HardcodeActivity.java` and `LogActivity.java`. Human QA removed redundant nested `Java.perform()` blocks and fixed `this.access.call(this, view)` to `this.access(view)`.
2. **`scripts/generated/frida_ssl_pinning_bypass.js`**
   - **Hallucination Caught:** Raw AI output hallucinated `android.net.http.SSLCertificateSocketFactory$TrustManager.onGetCertificateChain` and `okhttp3.OkHttp$CertificatePinner.pinToKeyStore`.
   - **Human QA Fix:** Replaced with real AOSP `javax.net.ssl.X509TrustManager` / `SSLContext.init` and `okhttp3.CertificatePinner.check(String, List)` hooks; V8 JS syntax check passed.

> **Honest Scope Note (per `01-LAB-SETUP-GUIDE.md §0.6`):** Due to host disk constraints (`8.53 GB` free on `C:`) and no rooted USB device attached during the solo sprint, Frida scripts were **statically syntax-verified and signature-verified against decompiled `jadx` classes**, with ready-to-run commands documented:
> `frida -U -f jakhar.aseem.diva -l scripts/generated/frida_diva_hardcode_hook.js`

---

## 4. Week 3 Validation & Hallucination Metrics

- **Total AI claims evaluated:** 12
- **Strictly Verified (`✅`):** 7 (**58.3%**)
- **Partially Correct (`⚠️`):** 2 (**16.7%**)
- **Hallucinated / Rejected (`❌`):** 3 (**25.0%**)
- **Week-over-Week Trend:** Strict verified accuracy improved from **50.0% (Week 2)** to **58.3% (Week 3)** as line-numbered ingest (`burp_to_context.py`, `mobile_to_context.py`) constrained model drift, though ungrounded API generation (`M2` generic SSL bypass) remained a clear hallucination source requiring human review.
