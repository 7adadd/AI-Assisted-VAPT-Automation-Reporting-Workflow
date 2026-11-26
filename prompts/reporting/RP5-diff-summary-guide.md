# RP5 — AI Draft vs Human Report Diff Audit Guide
## Phase
reporting
## Role
Quality-assurance reviewer (deterministic script + human audit; no LLM generation required for word-level diff).
## Variables
`{{ai_draft_path}}`, `{{human_edited_path}}`
## Anti-hallucination rules
GROUNDING RULES (mandatory):
1. Diff metrics must be computed deterministically by `scripts/reporting/diff_draft.py` using Python `difflib`.
2. Every removed hallucination or corrected CVSS score must cite the exact Finding ID and section.
3. Never fabricate diff percentages or edit counts.
4. Classify each human change honestly: Factual/CVSS Fix | Hallucination Removed | Evidence/PoC Added | Style/Clarity Edit.
5. Preserve both original AI draft and final human-edited versions unmodified for auditability.
## Template
Run `python scripts/reporting/diff_draft.py {{ai_draft_path}} {{human_edited_path}} --out deliverables/week4-hallucination-check-and-diff.md` and annotate the generated section-by-section diff table with human rationale for each correction.
## Expected output format
Automated diff statistics (lines added/removed, word-level similarity %, unified diff) + categorized human-correction audit table.
## Validation hook
Re-run `diff_draft.py` and verify reported statistics match the two Markdown files byte-for-byte.
## Tested with
Verified deterministically via `scripts/reporting/diff_draft.py`.
