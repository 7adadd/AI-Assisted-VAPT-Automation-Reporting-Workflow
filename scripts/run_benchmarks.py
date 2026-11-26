#!/usr/bin/env python3
"""Run the 6 fixed DEPI Week-1 benchmark tasks across local Llama & Qwen models.

Captures real Ollama telemetry (prompt tok/s, gen tok/s, load time, response text)
into `evidence/week1/benchmark-raw.json` and emits a markdown summary for
`lab/model-benchmarks.md`.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from vapt_ai import call_ollama  # noqa: E402

MODELS = ["llama3.2:3b", "qwen2.5:3b"]

TASKS = [
    {
        "id": "T1",
        "name": "Nmap Scan Triage",
        "system": "You are a VAPT analyst. Use ONLY facts in <DATA>, cite [nmap:port N], mark FACT/INFERENCE/UNKNOWN.",
        "prompt": (
            "Summarize this Nmap output into a priority table (Port, Service, Version, Observation, Citation) "
            "and top 3 non-destructive enumeration steps.\n<DATA>\n"
            "22/tcp   open  ssh         OpenSSH 9.6p1 Debian 3\n"
            "80/tcp   open  http        Apache httpd 2.4.62 ((Debian))\n"
            "|_http-title: Damn Vulnerable Web Application (DVWA) - Login\n"
            "445/tcp  open  microsoft-ds Samba smbd 4.24.6-Debian\n"
            "3306/tcp open  mysql       MariaDB 11.4.3\n"
            "</DATA>"
        ),
        "must_cite": ["80", "445", "3306", "22"],
    },
    {
        "id": "T2",
        "name": "BloodHound Edge Explanation",
        "system": "You are an AD analyst. Use ONLY <DATA>, cite [bh:edge], mark FACT/INFERENCE/UNKNOWN.",
        "prompt": (
            "Explain the attack path and abuse prerequisite from <DATA>:\n<DATA>\n"
            "[bh:edge E04] svc-sync@LAB.LOCAL --(GetChangesAll)--> LAB.LOCAL [Domain]\n"
            "[bh:edge E03] j.smith@LAB.LOCAL --(ForceChangePassword)--> svc-sync@LAB.LOCAL\n"
            "</DATA>"
        ),
        "must_cite": ["GetChangesAll", "ForceChangePassword", "svc-sync"],
    },
    {
        "id": "T3",
        "name": "XSS Payload Suggestion (Constrained)",
        "system": "You are a web security assistant. Only non-destructive PoC payloads. Cite parameter.",
        "prompt": (
            "Suggest 3 non-destructive reflected XSS payloads for parameter `name` in GET /dvwa/vulnerabilities/xss_r/?name=test. "
            "Constraint: max 45 characters each, no external callbacks.\n<DATA>\n"
            "GET /dvwa/vulnerabilities/xss_r/?name=hello HTTP/1.1\n"
            "Response body reflects: <pre>Hello hello</pre>\n</DATA>"
        ),
        "must_cite": ["name"],
    },
    {
        "id": "T4",
        "name": "Finding Paragraph Rewrite",
        "system": "You are a VAPT report editor. Use ONLY facts in <DATA>; do not invent CVEs or scores.",
        "prompt": (
            "Rewrite these raw notes into one concise professional VAPT finding paragraph (max 110 words).\n<DATA>\n"
            "Endpoint /dvwa/vulnerabilities/sqli/ param id=1' UNION SELECT user,password FROM users-- - "
            "returned database user admin and MD5 password hash from MariaDB.\n</DATA>"
        ),
        "must_cite": ["id", "users"],
    },
    {
        "id": "T5",
        "name": "PowerShell SPN Audit Script",
        "system": "Write strictly read-only PowerShell using ActiveDirectory module. No modifications.",
        "prompt": (
            "Write a read-only PowerShell one-liner or short snippet to list enabled AD user accounts "
            "with ServicePrincipalName set in domain LAB.LOCAL, selecting SamAccountName and ServicePrincipalNames."
        ),
        "must_cite": ["Get-ADUser", "ServicePrincipalName"],
    },
    {
        "id": "T6",
        "name": "Decompiled Java Review",
        "system": "You are a mobile code reviewer. Cite exact line numbers [jadx:L#] from <DATA>.",
        "prompt": (
            "Identify security vulnerabilities in this decompiled Android class with exact line numbers.\n<DATA>\n"
            "18: public void access(View view) {\n"
            "19:   EditText hkt = (EditText) findViewById(R.id.hcKey);\n"
            "20:   if (hkt.getText().toString().equals(\"vendorsecretkey\")) {\n"
            "21:     Log.d(\"DIVA-HC\", \"Access granted with key: \" + hkt.getText().toString());\n"
            "22:     Toast.makeText(this, \"Access granted!\", 0).show();\n"
            "23:   }\n24: }\n</DATA>"
        ),
        "must_cite": ["20", "21", "vendorsecretkey"],
    },
]


def score_response(resp: str, must_cite: list[str]) -> tuple[int, str]:
    hits = sum(1 for tok in must_cite if tok.lower() in resp.lower())
    ratio = hits / max(len(must_cite), 1)
    if not resp.strip():
        return 1, "empty response"
    if ratio == 1.0 and len(resp) >= 120:
        return 5, f"all {hits}/{len(must_cite)} required grounded elements present"
    if ratio >= 0.66:
        return 4, f"{hits}/{len(must_cite)} grounded elements present"
    if ratio >= 0.33:
        return 3, f"partial grounding ({hits}/{len(must_cite)})"
    return 2, f"weak grounding ({hits}/{len(must_cite)})"


def main() -> int:
    raw_out = ROOT / "evidence" / "week1" / "benchmark-raw.json"
    raw_out.parent.mkdir(parents=True, exist_ok=True)

    records = []
    for model in MODELS:
        print(f"=== Benchmarking {model} ===")
        for task in TASKS:
            print(f"  Running {task['id']} ({task['name']})...", flush=True)
            res = call_ollama(
                model=model,
                prompt=task["prompt"],
                system_prompt=task["system"],
                temperature=0.1,
                num_ctx=4096,
            )
            q_score, q_note = score_response(res["response"], task["must_cite"])
            rec = {
                "model": model,
                "task_id": task["id"],
                "task_name": task["name"],
                **res,
                "auto_grounding_score": q_score,
                "auto_grounding_note": q_note,
            }
            records.append(rec)
            print(
                f"    prompt={res['prompt_eval_tok_s']} tok/s, "
                f"gen={res['eval_tok_s']} tok/s, load={res['load_s']}s, "
                f"score={q_score}/5 ({q_note})"
            )
            time.sleep(0.3)

    raw_out.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OK saved raw benchmark telemetry -> {raw_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
