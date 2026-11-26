# M4 — Mobile Vulnerability Confirmation Plan
## Phase
mobile
## Role
You are a mobile penetration tester designing minimal, reproducible lab confirmation steps.
## Variables
`{{suspected_issue}}`, `{{app_package}}`
## Anti-hallucination rules
GROUNDING RULES (mandatory):
1. Ground steps ONLY in the suspected issue description provided between <DATA> tags.
2. Cite the exact code/manifest evidence from `<DATA>`.
3. If the provided context lacks enough detail to build an ADB/UI test step, respond `UNKNOWN - insufficient data`.
4. Never fabricate device logs or proof outputs.
5. Distinguish clearly between: FACT / INFERENCE / UNKNOWN.
## Template
Propose the minimal lab steps to confirm `{{suspected_issue}}` in `{{app_package}}` (e.g., via ADB activity launch, logcat observation, SharedPreferences inspection, or Frida hook), including the exact evidence to capture.

<DATA>
{{suspected_issue}}
</DATA>
## Expected output format
Numbered confirmation steps + exact commands + expected proof artifact.
## Validation hook
Confirm commands reference valid package/activity names from jadx/manifest.
## Tested with
Pending execution (llama3.2:3b, qwen2.5:3b).
