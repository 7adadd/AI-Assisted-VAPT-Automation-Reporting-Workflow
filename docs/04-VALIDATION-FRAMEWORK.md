# 04 — Validation Framework (Anti-Hallucination SOP)

This is the framework behind the program's required deliverables:
*"Validate all AI output manually"*, *"hallucination/accuracy review"*, *"hallucination check"*.

---

## 1. Principle

> **An AI claim is not a finding.** A finding is an AI claim that survived validation.

Every AI output that we intend to use (analysis, script, payload, report text) passes through the gate below and gets a row in the **Validation Log** (`evidence/validation-log.md`, gitignored; the *template and summary stats* are committed).

## 2. Validation levels

| Level | Name | What it means | When required |
|---|---|---|---|
| L0 | Rejected | Claim contradicted by data or unverifiable → discarded, logged as hallucination | — |
| L1 | **Data-verified** | Claim cites specific tool output; citation re-checked against the raw file | every factual claim |
| L2 | **Lab-executed** | Command/script/payload actually ran in the lab; result captured as evidence | every executable output |
| L3 | **Cross-model** | Second local model independently asked the same grounded question; answers compared | high-impact claims (attack paths, CVSS, "critical" findings) |
| L4 | Peer review | A second human reviewed the final claim/report | Week 4 final report |

Minimum acceptance: **L1 always, L2 for anything executable, L3 for high-impact, L4 for the final report.**

## 3. Validation Log (template)

File: `evidence/validation-log.md` — one table per week.

```markdown
# Validation Log — Week 2 (AD)

| ID | AI Claim / Output | Model | Source cited | Ground truth check | Result | Verdict |
|----|------------------|-------|--------------|--------------------|--------|---------|
| W2-001 | "User svc-backup is Kerberoastable due to SPN HTTP/dc.lab.local" | llama3.1:8b | [sharphound.json:edge] | BloodHound GUI + Get-ADUser -Properties ServicePrincipalNames | SPN confirmed, no preauth not claimed | ✅ L1+L3 |
| W2-002 | "PowerShell script lists writable GPOs" | qwen2.5:7b | script | ran in lab | ran clean, 2 GPOs found | ✅ L2 |
| W2-003 | "User 'helpdesk' can DCSync" | llama3.1:8b | (no source) | BloodHound: no such edge | invented edge | ❌ hallucination |
```

Verdict vocabulary: ✅ verified · ⚠️ partially correct (note exactly what was wrong) · ❌ hallucination · ❔ UNKNOWN (insufficient data — may re-prompt with more data).

## 4. Accuracy metrics (required for the review deliverable)

At the end of each week compute and commit (numbers only, log stays local):

```markdown
## Week 2 — AI Accuracy Review
- Total AI claims used:        24
- Verified (L1/L2/L3):         19  (79.2%)
- Partially correct:            3  (12.5%)
- Hallucinations:               2  ( 8.3%)
- Common failure patterns: inventing AD edges absent from data; wrong cmdlet names in scripts; overconfident CVSS scores
- Mitigations applied: added citation rule to AD1 template; switched script-gen to deepseek-coder:6.7b
```

**Trend target:** hallucination rate decreasing week-over-week as templates improve — this trend is itself a presentation highlight.

## 5. Ground-truth sources per phase

| Phase | Ground truth = |
|---|---|
| Recon | the raw Nmap/enum outputs themselves |
| AD | BloodHound GUI + `Get-AD*` verification commands + actual script execution |
| Web | DVWA/Juice Shop actual responses + screenshots |
| Mobile | actual Frida hook output / emulator behavior |
| Reporting | official CVSS calculator + human editor |

## 6. Prompting techniques that reduce hallucination

1. **Grounding block** in every template (see doc 02) — "only provided data, cite, else UNKNOWN".
2. **Fact/Inference/Unknown labeling** — forces the model to separate claims.
3. **Two-model cross-check** for critical claims.
4. **Smaller context, cleaner data** — ingest scripts strip noise so the model has only relevant facts.
5. **Never ask for facts the data doesn't contain** (e.g., don't ask "which CVEs affect this version" from thin air — if a CVE check is wanted, it's a separate, explicitly-marked web-knowledge task, and its output is verified against vendor advisories).
6. **Re-prompt on UNKNOWN** with the missing data instead of accepting a guess.

## 7. Weekly hallucination-check deliverable (Week 4)

Final deliverable = the compiled accuracy review across all weeks:
- totals per week + trend chart (can be a simple table/chart in the presentation)
- top failure patterns + how the template library evolved to prevent them
- statement of remaining limitations (honest scope)
