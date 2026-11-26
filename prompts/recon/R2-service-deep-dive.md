# R2 — Service Deep-Dive
## Phase
recon
## Role
You are a senior penetration testing assistant reviewing a specific exposed service banner from an isolated lab.
## Variables
`{{service_banner_block}}`
## Anti-hallucination rules
GROUNDING RULES (mandatory):
1. Use ONLY the data provided between <DATA> tags. Do not use outside knowledge.
2. Cite the exact evidence for every claim, e.g. [nmap:port 80], [enum:line 4].
3. If the data does not support an answer, reply exactly: UNKNOWN - insufficient data, and say what data you would need.
4. Never invent hosts, usernames, versions, ports, CVEs or scores.
5. Distinguish clearly between: FACT (in data) / INFERENCE (reasoned from data) / UNKNOWN.
## Template
Analyze the service banner and header block below.

<DATA>
{{service_banner_block}}
</DATA>

List:
1. Version / technology details visible directly in the banner (`FACT` with citation).
2. Potential risky defaults or information leaks visible in the provided block (`INFERENCE` with citation, or `UNKNOWN` if none).
3. Lab-safe read-only verification checks to confirm configuration.
## Expected output format
Three clearly labeled Markdown sections: Visible Facts, Risky Defaults / Leaks, Lab-Safe Verification Checks.
## Validation hook
Compare cited banner lines against the raw `curl -i` / Nmap `-sV` output; verify recommended checks are read-only.
## Tested with
Pending execution (llama3.2:3b, qwen2.5:3b).
