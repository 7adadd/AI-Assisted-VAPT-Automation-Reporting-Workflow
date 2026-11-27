# 03 — Privacy & Ethics Checklist (mandatory)

> **This checklist is a hard gate.** It must be fully ✅ before any test in any week.
> Failure of a single item = stop testing until resolved.

---

## 1. Privacy rules (local AI)

| # | Rule | Why |
|---|---|---|
| P1 | Inference uses the local Ollama loopback endpoint by default; verify its configured URL before each run. | Keep prompts local |
| P2 | PortSwigger import/inspection makes outbound HTTPS requests to the selected PortSwigger host; this is not offline/air-gapped mode. | Make network behavior explicit |
| P3 | The Port Solver actively sends bounded requests only to the selected per-user `*.web-security-academy.net` instance. State-changing POST requests require the GUI consent checkbox. | Authorized training scope only |
| P4 | `evidence/` and `reports/` are gitignored by default; review any deliverable explicitly added to Git before pushing. | Avoid accidental data disclosure |
| P4 | Before pushing any file to GitHub: search it for usernames, IPs, hostnames, domains, screenshots. | Accidental leak prevention |
| P5 | Redact real personal data from **any** artifact that could be shared (this project uses no real data at all). | Compliance |

**Data handling matrix**

| Data type | May enter prompts? | May enter repo? | May enter evidence/ (gitignored)? |
|---|---|---|---|
| Synthetic lab configuration (no credentials) | ✅ yes | ✅ sanitized config only | ✅ if needed |
| Lab HTTP captures/screenshots | ✅ minimize/redact first | only sanitized examples | local, gitignored by default |
| Real client or third-party data | ❌ never in this project | ❌ never | ❌ never |
| Passwords, session cookies, API keys (even lab-generated) | use only when strictly needed; do not send to the model unless redacted/necessary | ❌ never | ❌ never; redact before logging |

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
[ ] P1 — Ollama URL is local (`127.0.0.1`/`localhost`); no cloud inference selected
[ ] P2 — if importing/inspecting a lab URL, it is an intended PortSwigger Academy host
[ ] P3 — if solving actively, I own/was assigned this instance and understand POST/state changes
[ ] P4 — `git status` reviewed; staged files contain no secrets or unrelated lab data
[ ] E1 — every active target is an authorized training instance or self-owned lab
[ ] E4 — inspect the proposed action and evidence; use consent only for this lab run
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
