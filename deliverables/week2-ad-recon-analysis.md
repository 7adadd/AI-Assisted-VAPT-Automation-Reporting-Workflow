# Week 2 Deliverable — AI-Assisted Recon & Active Directory Analysis

**Engagement Scope:** Isolated Kali WSL2 Lab (`127.0.0.1`) + Lab AD Graph (`LAB.LOCAL`)  
**Models Evaluated:** `qwen2.5:3b` (Primary) & `llama3.2:3b` (Cross-Check)  
**Author:** Mohamed Reda Elhaddad (`@7adadd`) · **Date:** 2026-11-26

---

## 1. Reconnaissance Phase (Real Kali WSL Scan & Banner Enum)

### 1.1 Ground-Truth Tool Output (`nmap -sV -sC`)
Executed inside Kali WSL against local lab services (`evidence/week2/nmap-lab.xml`) and stripped via `scripts/ingest/nmap_to_context.py`:

| Port / Proto | State | Service | Verified Version |
|---|---|---|---|
| `80/tcp` | `open` | `http` | `Apache httpd 2.4.68 (Debian)` (hosting DVWA) |
| `3306/tcp` | `open` | `mysql` | `11.8.8-MariaDB-1 from Debian` (`mysql_native_password`, TLS enabled) |
| `8888/tcp` | `open` | `http` | `Werkzeug httpd 3.1.9 (Python 3.14.6)` |
| `22, 443, 445, 8080` | `closed` | — | Verified closed in Nmap XML |

### 1.2 Cross-Model Triage Comparison (`R1` / `R2` / `R3`)
- **`qwen2.5:3b` (`ai-R1-qwen.md`):** Correctly mapped all 3 open ports and 4 closed ports with exact `[nmap:port ...]` citations in **16.3s** (`70.2 tok/s`). Only minor flaw: Step 5 of next-steps still listed closed port `8080/tcp`.
- **`llama3.2:3b` (`ai-R1-llama.md`, `ai-R2-llama.md`):** Placed `Werkzeug httpd 3.1.9` under `80/tcp` instead of `8888/tcp`, overclaimed `"Apache default page is vulnerable to exploitation"`, and misinterpreted PHP's standard `Expires: Tue, 23 Jun 2009` anti-cache header as a broken session expiration mechanism.

---

## 2. Active Directory Attack-Path & Permission Analysis (`LAB.LOCAL`)

### 2.1 Deterministic BFS Ground Truth (`bloodhound_to_context.py`)
`scripts/ingest/bloodhound_to_context.py` parsed `lab/ad-lab-dataset/bloodhound_lab.json` (11 nodes, 8 edges) and solved shortest attack paths to high-value targets (`DOMAIN ADMINS@LAB.LOCAL` / `LAB.LOCAL`) while ignoring benign `ReadGPO` edges:

1. **Path A (3 hops — ACL + Group Chain):**
   `m.ali@LAB.LOCAL` —`[E01: GenericAll]`→ `svc-backup@LAB.LOCAL` (Kerberoastable SPN `MSSQLSvc/db01.lab.local:1433`) —`[E02: MemberOf]`→ `IT-ADMINS@LAB.LOCAL` —`[E03: WriteDacl]`→ `DOMAIN ADMINS@LAB.LOCAL`
2. **Path B (2 hops — AS-REP + Password Reset + DCSync):**
   `j.smith@LAB.LOCAL` (`DONT_REQ_PREAUTH`) —`[E04: ForceChangePassword]`→ `svc-sync@LAB.LOCAL` —`[E05/E06: GetChangesAll + GetChanges]`→ `LAB.LOCAL` (Domain-level DCSync)
3. **Decoy Principals (Must Return No Path):**
   `helpdesk01@LAB.LOCAL` (`MemberOf HELP-DESK`, `ReadGPO` only — though its `description` contains `TempPass2026!`) and `s.nabil@LAB.LOCAL` (`null` path).

### 2.2 AI Analysis vs. Ground Truth (`AD1`, `AD2`, `AD4`, `AD5`)
- **Attack Paths (`AD1`):**
  - `qwen2.5:3b` nailed Path A (`E01 -> E02 -> E03`), **but hallucinated** a fake 5-hop continuation on Path B (`E02: svc-sync --MemberOf--> IT-Admins`) because it did not stop at domain-level `LAB.LOCAL` DCSync.
  - `llama3.2:3b` correctly identified `E01->E02->E03` and `E04->E05/E06` (admitting `[No direct edge]` after `LAB.LOCAL`), **but** left its summary table empty and failed to name `DCSync` / `WriteDacl AddMember` abuse techniques.
- **ACL Anomaly Audit (`AD2`):**
  - `qwen2.5:3b` cleanly extracted all **5/5 dangerous ACEs** (`m.ali GenericAll`, `IT-Admins WriteDacl`, `j.smith ForceChangePassword`, `svc-sync GetChangesAll/GetChanges`) and ignored benign `ReadProperty`/`GenericRead` rows (`[6]`/`[7]`).
- **Enum4linux Triage (`AD4`) & Kerberoasting/AS-REP (`AD5`):**
  - `qwen2.5:3b` extracted `helpdesk01` (`TempPass2026!`) and `DeptDocs (READ/WRITE for Authenticated Users)` accurately, and correctly identified `j.smith` as AS-REP Roastable.
  - `llama3.2:3b` **hallucinated a full account swap in `AD5`**, labeling `j.smith` as Kerberoasting and `IT-Admins` (a group!) as AS-REP Roastable, plus invented invalid Windows flags (`klist /me`, `klist /user:...`).

---

## 3. AI-Generated Audit Scripts & L2 Validation (`scripts/generated/`)

Four read-only audit scripts were generated via `AD3` (`qwen2.5:3b`) and validated before acceptance:

| Script | Language | Validation Method | Raw AI Defect Caught | Final Status |
|---|---|---|---|---|
| `ad_spn_audit.ps1` | PowerShell | PowerShell AST Parser | Repetitive trailing checklist comments | ✅ **0 syntax errors**, read-only `Get-ADUser` verified |
| `ad_acl_audit.ps1` | PowerShell | PowerShell AST Parser + Logic Review | Raw AI iterated group members instead of `AD:\` `Get-Acl` ACEs | ✅ Fixed to inspect real ACEs; **0 syntax errors** |
| `nmap_triage_verifier.py` | Python | Live execution on `nmap-lab.xml` | Raw AI checked `port.get('state')` & `host.get('host_name')` instead of child `<state>` / `<address>` elements | ✅ Fixed & executed cleanly (3 open ports output) |
| `bh_path_auditor.py` | Python | Live execution on `bloodhound_lab.json` | Raw AI guessed `users`/`Kerberoastable` keys & used `and` across mutually exclusive rights | ✅ Fixed & executed cleanly (lists `svc-backup`, `j.smith`, 5 edges) |

---

## 4. Week 2 Validation & Hallucination Metrics

- **Total AI claims evaluated:** 12
- **Strictly Verified (`✅`):** 6 (**50.0%**)
- **Partially Correct (`⚠️`, usable after minor human fix):** 3 (**25.0%**)
- **Hallucinated / Rejected (`❌`):** 3 (**25.0%**)
- **Primary Failure Patterns Observed:** XML/JSON schema assumptions in generated code (`nmap_triage_verifier.py`, `bh_path_auditor.py`), port/account swapping in 3B models (`llama3.2:3b` in `R1`/`AD5`), and connecting finished domain-level DCSync paths to extra group edges (`qwen2.5:3b` in `AD1`).
