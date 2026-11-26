# 03 — Privacy & Ethics Checklist (mandatory)

> **This checklist is a hard gate.** It must be fully ✅ before any test in any week.
> Failure of a single item = stop testing until resolved.

---

## 1. Privacy rules (local AI)

| # | Rule | Why |
|---|---|---|
| P1 | All LLM inference is **local** (Ollama/LM Studio/GPT4All). No cloud API keys configured. | Test data must never leave the machine |
| P2 | No telemetry/cloud sync enabled in any AI runtime where avoidable. | Same reason |
| P3 | `evidence/` and `reports/` are **gitignored** — raw tool output, screenshots and reports are never pushed to GitHub. | Repos are public |
| P4 | Before pushing any file to GitHub: search it for usernames, IPs, hostnames, domains, screenshots. | Accidental leak prevention |
| P5 | Redact real personal data from **any** artifact that could be shared (this project uses no real data at all). | Compliance |

**Data handling matrix**

| Data type | May enter prompts? | May enter repo? | May enter evidence/ (gitignored)? |
|---|---|---|---|
| Lab VM data (lab.local, DIVA, DVWA…) | ✅ yes | ✅ yes (configs) | ✅ yes |
| Own screenshots of lab | ✅ yes | ❌ no | ✅ yes |
| Real client data | ❌ **never** | ❌ never | ❌ never (out of scope) |
| API keys / passwords (lab) | ✅ yes (fake ones) | ❌ no | ✅ yes |

---

## 2. Ethics rules (authorized testing only)

| # | Rule |
|---|---|
| E1 | **Test only machines you own or have explicit written authorization to test.** This project's scope is the self-built lab only. |
| E2 | No scanning, probing or testing of any third-party/public system — including "just to try". |
| E3 | If the workflow is ever reused on a real engagement: written authorization, defined scope, defined time window, and a contact for incident escalation are **prerequisites**. |
| E4 | AI is an assistant, not the operator. **Every** action (command, script, payload) is reviewed by a human before execution. |
| E5 | AI-generated scripts are never run with elevated privileges on first run; they run in the lab, read-only first. |
| E6 | Non-destructive testing only in this project: no data destruction, no persistence mechanisms, no denial-of-service. |
| E7 | AI assistance is **disclosed** in the report methodology ("AI-assisted with human validation — see SOP"). |
| E8 | Findings and severity are owned by the human analyst. AI drafts are inputs, not conclusions. |

---

## 3. Pre-session checklist (tick each working session)

```
[ ] P1 — Ollama/LM Studio/GPT4All in local mode (no cloud models selected)
[ ] P4 — nothing sensitive is queued for commit (git status reviewed)
[ ] E1 — every target about to be touched is a lab VM I own
[ ] E4 — plan reviewed: each AI suggestion has a human review step
[ ] Snapshots: vulnerable-ad / clean-kali exist and are current
```

## 4. Pre-push checklist (before `git push`)

```
[ ] git status — only intended files staged
[ ] grep for lab hostnames/IPs in files that will be pushed (configs belong in templates, not outputs)
[ ] No screenshots in the repo (they belong in evidence/, gitignored)
[ ] No model outputs containing credentials pushed
```

## 5. Incident rule

If anything unintended leaves the machine (accidental push of sensitive data, testing outside lab scope): **stop immediately**, document what happened in a note, and fix/rotate/remove. Transparency first.
