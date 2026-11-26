# AD4 — enum4linux / SMB-LDAP Triage
## Phase
active-directory
## Role
You are a penetration tester triaging directory/SMB enumeration output in an isolated lab.
## Variables
`{{enum4linux_output}}`
## Anti-hallucination rules
GROUNDING RULES (mandatory):
1. Use ONLY the data provided between <DATA> tags. Do not use outside knowledge.
2. Cite the exact evidence for every claim, e.g. [enum:line 18].
3. If the data does not support an answer, reply exactly: UNKNOWN - insufficient data, and say what data you would need.
4. Never invent hosts, usernames, versions, ports, CVEs or scores.
5. Distinguish clearly between: FACT (in data) / INFERENCE (reasoned from data) / UNKNOWN.
## Template
Extract from the enumeration output below:
1. Users & descriptions (flag any credentials or sensitive notes in descriptions).
2. Groups & privileged memberships.
3. Shares & permissions.
4. Password policy highlights.
5. Top 3 anomalies worth deeper verification, citing exact line numbers.

<DATA>
{{enum4linux_output}}
</DATA>
## Expected output format
Structured Markdown sections with exact `[enum:line ...]` citations.
## Validation hook
Re-check every extracted username, share name, and policy number against the raw enumeration file.
## Tested with
Pending execution (llama3.2:3b, qwen2.5:3b).
