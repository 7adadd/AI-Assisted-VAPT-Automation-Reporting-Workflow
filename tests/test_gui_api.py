#!/usr/bin/env python3
"""API smoke tests for the localhost FastAPI VAPT Automation GUI."""
from __future__ import annotations

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000"


def main() -> int:
    print("1. GET /api/health")
    r = requests.get(f"{BASE}/api/health", timeout=10)
    assert r.status_code == 200, r.text
    h = r.json()
    assert h["privacy_mode"] == "127.0.0.1-only"
    assert h["ollama_connected"] is True
    assert h["stats"]["total_prompts"] == 23

    print("2. GET /api/benchmarks")
    r = requests.get(f"{BASE}/api/benchmarks", timeout=10)
    assert r.status_code == 200
    b = r.json()
    assert len(b["tasks"]) == 6

    print("3. GET /api/prompts")
    r = requests.get(f"{BASE}/api/prompts", timeout=10)
    assert r.status_code == 200
    assert r.json()["total"] == 23

    print("4. GET /api/samples & /api/challenges")
    assert requests.get(f"{BASE}/api/samples", timeout=10).status_code == 200
    c = requests.get(f"{BASE}/api/challenges", timeout=10)
    assert c.status_code == 200 and len(c.json()["challenges"]) == 12

    print("5. GET /api/ad-graph")
    r = requests.get(f"{BASE}/api/ad-graph", timeout=10)
    assert r.status_code == 200
    g = r.json()
    assert len(g["nodes"]) == 11 and len(g["edges"]) == 8
    assert "E01" in g["highlighted_edges"]

    print("6. POST /api/cvss (valid + invalid)")
    r = requests.post(f"{BASE}/api/cvss", json={"vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}, timeout=10)
    assert r.status_code == 200 and r.json()["base_score"] == 9.8
    bad = requests.post(f"{BASE}/api/cvss", json={"vector": "INVALID"}, timeout=10)
    assert bad.status_code == 400

    print("7. GET /api/report/diff")
    r = requests.get(f"{BASE}/api/report/diff", timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["stats"]["word_similarity_pct"] > 0 and len(d["pocs"]) == 5

    print("8. POST /api/analyze (file upload)")
    sample_file = ROOT / "lab" / "challenge-samples" / "portswigger" / "ps-01-ssrf-stock-check.http"
    with sample_file.open("rb") as fh:
        r = requests.post(
            f"{BASE}/api/analyze",
            files={"file": (sample_file.name, fh, "text/plain")},
            data={"template_id": "W1", "model": "qwen2.5:3b", "artifact_type": "http"},
            timeout=120,
        )
    assert r.status_code == 200, r.text
    assert "ssrf" in r.json()["output"].lower() or "stockapi" in r.json()["output"].lower()

    print("9. POST /api/cross-check")
    r = requests.post(
        f"{BASE}/api/cross-check",
        json={"sample_id": "dvwa-04", "template_id": "W1", "artifact_type": "http"},
        timeout=180,
    )
    assert r.status_code == 200, r.text
    cc = r.json()
    assert cc["qwen"]["response"] and cc["llama"]["response"]

    print("10. POST /api/validation-log (with clean restore)")
    deliv_log = ROOT / "deliverables" / "validation-log.md"
    ev_log = ROOT / "evidence" / "validation-log.md"
    orig_deliv = deliv_log.read_text(encoding="utf-8")
    orig_ev = ev_log.read_text(encoding="utf-8") if ev_log.exists() else None
    try:
        before_cnt = requests.get(f"{BASE}/api/validation-log", timeout=10).json()["total"]
        vr = requests.post(
            f"{BASE}/api/validation-log",
            json={"phase": "GUI Test", "claim": "Smoke test claim", "model": "qwen2.5:3b", "result": "OK", "verdict": "Verified"},
            timeout=10,
        )
        assert vr.status_code == 200 and vr.json()["total"] == before_cnt + 1
    finally:
        deliv_log.write_text(orig_deliv, encoding="utf-8")
        if orig_ev is not None:
            ev_log.write_text(orig_ev, encoding="utf-8")

    print("11. POST /api/report/export")
    er = requests.post(f"{BASE}/api/report/export", json={"target": "presentation"}, timeout=60)
    assert er.status_code == 200 and er.json()["files"][0]["bytes"] > 10000

    print("ALL 11 API SMOKE TESTS PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
