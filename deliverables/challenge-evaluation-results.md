# Passive Challenge Evaluation Results — DVWA & PortSwigger (12 Patterns)

- **Model:** `qwen2.5:3b` via `POST /api/analyze` (`W1` Burp HTTP Request Explainer)
- **Mode:** 100% passive local HTTP capture analysis (zero live attacking)
- **Diagnosis Accuracy:** **12 / 12 (100.0%)**

| ID | Suite | Challenge | Expected Class | Matched Signals | Cited Line? | Speed | Verdict |
|---|---|---|---|---|---|---|---|
| `dvwa-01` | DVWA | SQL Injection (UNION) | SQL Injection | sql, id | Yes | 56.96 tok/s | ✅ Diagnosed |
| `dvwa-02` | DVWA | Reflected XSS | Cross-Site Scripting | xss, name | Yes | 68.23 tok/s | ✅ Diagnosed |
| `dvwa-03` | DVWA | Stored XSS | Cross-Site Scripting | xss, mtxmessage | Yes | 68.92 tok/s | ✅ Diagnosed |
| `dvwa-04` | DVWA | OS Command Injection | Command Injection | command, ip | Yes | 67.77 tok/s | ✅ Diagnosed |
| `dvwa-05` | DVWA | Local File Inclusion | Path Traversal / File Inclusion | traversal, page | Yes | 65.7 tok/s | ✅ Diagnosed |
| `dvwa-06` | DVWA | CSRF Password Change | Cross-Site Request Forgery | csrf, password_new | Yes | 67.29 tok/s | ✅ Diagnosed |
| `ps-01` | PortSwigger | SSRF Stock Check | Server-Side Request Forgery (SSRF) | stockapi | Yes | 68.39 tok/s | ✅ Diagnosed |
| `ps-02` | PortSwigger | XXE External Entity | XML External Entity (XXE) | xxe, xml, entity | Yes | 70.15 tok/s | ✅ Diagnosed |
| `ps-03` | PortSwigger | SSTI Template Injection | Server-Side Template Injection (SSTI) | template, message | Yes | 69.96 tok/s | ✅ Diagnosed |
| `ps-04` | PortSwigger | IDOR Account Exposure | Insecure Direct Object Reference (IDOR) | id | Yes | 70.01 tok/s | ✅ Diagnosed |
| `ps-05` | PortSwigger | JWT Unverified Signature (alg=none) | Broken Authentication / JWT Flaw | jwt, session | Yes | 70.2 tok/s | ✅ Diagnosed |
| `ps-06` | PortSwigger | Error-Based SQLi in Cookie | SQL Injection | sql, trackingid | Yes | 70.45 tok/s | ✅ Diagnosed |
