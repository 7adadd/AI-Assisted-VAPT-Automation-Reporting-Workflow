#!/usr/bin/env python3
"""Offline FastAPI tests through TestClient; no server/Ollama/network writes."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["VAPT_STUDIO_SESSION_TOKEN"] = "unit-test-token"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

HEADERS = {"Origin": "http://127.0.0.1:8000", "X-VAPT-Session": "unit-test-token"}


class LocalAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, base_url="http://127.0.0.1:8000")

    def test_read_only_endpoints(self):
        for path in ("/api/health", "/api/benchmarks", "/api/prompts", "/api/samples", "/api/challenges", "/api/ad-graph", "/api/report/diff"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        health = self.client.get("/api/health").json()
        self.assertEqual(health["privacy_mode"], "127.0.0.1-only")
        self.assertGreaterEqual(health["stats"]["total_prompts"], 24)
        self.assertEqual(health["stats"]["total_findings"], 9)
        self.assertEqual(health["stats"]["validation"]["total"], 24)
        self.assertEqual(health["stats"]["validation"]["verified"], 13)
        self.assertTrue(any(p["id"] == "PS1" for p in self.client.get("/api/prompts").json()["items"]))
        self.assertEqual(len(self.client.get("/api/challenges").json()["challenges"]), 12)

    def test_mutating_api_requires_session_token_and_origin(self):
        payload = {"vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}
        self.assertEqual(self.client.post("/api/cvss", json=payload).status_code, 403)
        self.assertEqual(self.client.post("/api/cvss", json=payload, headers={**HEADERS, "Origin": "https://evil.example"}).status_code, 403)
        r = self.client.post("/api/cvss", json=payload, headers=HEADERS)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["base_score"], 9.8)

    def test_scope_guards_reject_external_urls_without_fetching(self):
        cases = [
            ("/api/lab/import", {"url": "http://169.254.169.254/latest/meta-data/"}),
            ("/api/lab/inspect", {"url": "https://portswigger.net/web-security/"}),
            ("/api/port-solver/solve", {"url": "https://evil.example/"}),
        ]
        with patch("requests.get", side_effect=AssertionError("must not perform network IO")):
            for path, payload in cases:
                with self.subTest(path=path):
                    r = self.client.post(path, json=payload, headers=HEADERS)
                    self.assertEqual(r.status_code, 400)

    def test_analyzer_input_size_limit(self):
        r = self.client.post("/api/analyze", json={"raw_text": "x" * (2 * 1024 * 1024 + 1)}, headers=HEADERS)
        self.assertEqual(r.status_code, 413)

    def test_export_alias_matches_report_button(self):
        with patch("app.main.subprocess.run") as run:
            r = self.client.post("/api/report/export", json={"target": "report"}, headers=HEADERS)
        self.assertEqual(r.status_code, 200)
        run.assert_called_once()

    def test_solver_called_once_and_consent_forwarded(self):
        from app.main import app
        from scripts.port_solver import SolveResult
        fake = SolveResult(lab_type="agentic", title="test", solved=False, payload="", method="", status=200,
                           evidence="mock evidence", explanation="mock", state="not_solved", source="agentic")
        with patch("agentic_solver.agentic_solve", return_value=fake) as solver, patch(
            "port_solver.solve_lab", side_effect=AssertionError("playbook must not run implicitly")
        ):
            r = self.client.post("/api/port-solver/solve",
                                 json={"url":"https://abc.web-security-academy.net/", "description":"desc", "allow_state_changes":True},
                                 headers=HEADERS)
        self.assertEqual(r.status_code, 200, r.text)
        solver.assert_called_once_with("https://abc.web-security-academy.net/", hints=[], description="desc", allow_state_changes=True)
        self.assertEqual(r.json()["status"], "not_solved")


if __name__ == "__main__":
    unittest.main(verbosity=2)
