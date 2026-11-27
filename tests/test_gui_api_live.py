#!/usr/bin/env python3
"""Optional live integration tests: requires running GUI, Ollama, and network access.

Run only when intentionally testing those integrations:
    VAPT_RUN_LIVE_TESTS=1 python tests/test_gui_api_live.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"


def main() -> int:
    if os.environ.get("VAPT_RUN_LIVE_TESTS") != "1":
        print("SKIP: set VAPT_RUN_LIVE_TESTS=1 to enable live Ollama/PortSwigger tests")
        return 0

    health = requests.get(f"{BASE}/api/health", timeout=10).json()
    if not health.get("ollama_connected"):
        raise SystemExit("Ollama is not reachable at the configured local endpoint")

    # Keep this test non-mutating: import only a public PortSwigger description page.
    r = requests.post(
        f"{BASE}/api/lab/import",
        json={"url": "https://portswigger.net/web-security/sql-injection/lab-retrieve-hidden-data"},
        timeout=45,
    )
    assert r.status_code == 200, r.text[:200]
    meta = r.json()["metadata"]
    assert "SQL injection" in meta["title"]
    assert len(meta["description"]) > 40
    print("PASS live PortSwigger description import")
    print("Live solver tests require a user-supplied active lab instance and explicit consent in the GUI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
