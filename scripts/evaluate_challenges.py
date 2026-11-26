#!/usr/bin/env python3
"""Passively evaluate all 12 local DVWA & PortSwigger challenge captures via /api/analyze."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000"

EXPECTED_KEYWORDS = {
    "dvwa-01": ["sql", "id"],
    "dvwa-02": ["xss", "script", "name"],
    "dvwa-03": ["xss", "mtxmessage"],
    "dvwa-04": ["command", "ip"],
    "dvwa-05": ["file inclusion", "traversal", "page"],
    "dvwa-06": ["csrf", "password_new"],
    "ps-01": ["ssrf", "request forgery", "stockapi"],
    "ps-02": ["xxe", "xml", "entity"],
    "ps-03": ["template", "ssti", "message"],
    "ps-04": ["idor", "access control", "id"],
    "ps-05": ["jwt", "none", "session"],
    "ps-06": ["sql", "trackingid"],
}


def main() -> int:
    challenges = requests.get(f"{BASE}/api/challenges", timeout=10).json()["challenges"]
    results = []
    passed_cnt = 0

    for ch in challenges:
        cid = ch["id"]
        print(f"Evaluating [{ch['suite']}] {cid} ({ch['name']})...", flush=True)
        resp = requests.post(
            f"{BASE}/api/analyze",
            json={
                "sample_id": cid,
                "artifact_type": "http",
                "template_id": "W1",
                "model": "qwen2.5:3b",
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        out_low = data["output"].lower()
        kws = EXPECTED_KEYWORDS[cid]
        hits = [kw for kw in kws if kw in out_low]
        has_citation = "[http:line" in out_low or "line " in out_low
        passed = (len(hits) >= 2 or (len(hits) == 1 and ch["target_param"].lower() in out_low)) and has_citation
        if passed:
            passed_cnt += 1

        tel = data["telemetry"]
        results.append({
            "id": cid,
            "suite": ch["suite"],
            "name": ch["name"],
            "expected_vuln": ch["expected_vuln"],
            "target_param": ch["target_param"],
            "matched_keywords": hits,
            "has_citation": has_citation,
            "passed": passed,
            "gen_tps": tel["eval_tok_s"],
            "total_s": tel["total_s"],
            "output_excerpt": data["output"][:360],
        })
        print(f"  -> passed={passed} hits={hits} cite={has_citation} ({tel['eval_tok_s']} tok/s)", flush=True)

    total = len(results)
    summary = {
        "total": total,
        "passed": passed_cnt,
        "pass_rate_pct": round((passed_cnt / total) * 100, 1) if total else 0.0,
        "model": "qwen2.5:3b",
        "template": "W1",
    }
    eval_json = ROOT / "deliverables" / "challenge-evaluation.json"
    eval_json.write_text(json.dumps({"summary": summary, "results": results}, indent=2), encoding="utf-8")

    md = [
        "# Passive Challenge Evaluation Results — DVWA & PortSwigger (12 Patterns)",
        "",
        f"- **Model:** `qwen2.5:3b` via `POST /api/analyze` (`W1` Burp HTTP Request Explainer)",
        f"- **Mode:** 100% passive local HTTP capture analysis (zero live attacking)",
        f"- **Diagnosis Accuracy:** **{summary['passed']} / {summary['total']} ({summary['pass_rate_pct']}%)**",
        "",
        "| ID | Suite | Challenge | Expected Class | Matched Signals | Cited Line? | Speed | Verdict |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        md.append(
            f"| `{r['id']}` | {r['suite']} | {r['name']} | {r['expected_vuln']} | "
            f"{', '.join(r['matched_keywords'])} | {'Yes' if r['has_citation'] else 'No'} | "
            f"{r['gen_tps']} tok/s | {'✅ Diagnosed' if r['passed'] else '⚠️ Partial'} |"
        )
    eval_md = ROOT / "deliverables" / "challenge-evaluation-results.md"
    eval_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"OK saved {eval_json} & {eval_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
