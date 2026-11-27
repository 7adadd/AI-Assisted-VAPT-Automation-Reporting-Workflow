#!/usr/bin/env python3
"""Offline solver security and success-state tests."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import agentic_solver  # noqa: E402
from agentic_solver import Action, _action_needs_confirmation, _parse_plan, _observed_path  # noqa: E402
from vapt_ai import find_template  # noqa: E402
from lab_inspect import inspect_lab
from port_solver import SolveResult, _congratulated, _detect, _waf_rejected, official_state  # noqa: E402
from safe_lab_http import ScopedLabSession, validate_instance_url  # noqa: E402


class OfficialSolveSignalTests(unittest.TestCase):
    def test_only_official_banner_is_success(self):
        self.assertTrue(_congratulated('<section id="notification-labsolved"><h4>Congratulations, you solved the lab!</h4></section>'))
        self.assertTrue(_congratulated('{"correct":true}'))
        self.assertFalse(_congratulated('<html><script>alert(1)</script> reflected</html>'))
        self.assertFalse(_congratulated('<div>administrator delete panel</div>'))
        self.assertFalse(_congratulated('<div>root:x:0:0</div>'))
        self.assertFalse(_congratulated('<p>admin page available</p>'))

    def test_expired_and_blocked_states(self):
        self.assertEqual(official_state("expired", 504), "expired")
        self.assertEqual(official_state("blocked", 403), "blocked")
        self.assertEqual(official_state("ordinary page", 200), "not_solved")

    def test_already_solved_state_is_preserved(self):
        result = SolveResult(lab_type="test", title="test", solved=True, payload="", method="GET", status=200,
                             evidence="official banner", explanation="already solved", state="already_solved")
        self.assertEqual(result.state, "already_solved")


class NetworkScopeTests(unittest.TestCase):
    def test_validate_https_instance(self):
        origin, host = validate_instance_url("https://abc123.web-security-academy.net/path")
        self.assertEqual(origin, "https://abc123.web-security-academy.net")
        self.assertEqual(host, "abc123.web-security-academy.net")

    def test_reject_bad_authorities(self):
        urls = [
            "http://abc.web-security-academy.net/",
            "https://abc.web-security-academy.net:8443/",
            "https://user:pw@abc.web-security-academy.net/",
            "https://web-security-academy.net/",
            "https://evil.example/",
        ]
        for url in urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_instance_url(url)

    def test_redirect_is_rejected_without_follow(self):
        s = ScopedLabSession("abc.web-security-academy.net")
        response = Mock(status_code=302, headers={"Location": "https://evil.example/"})
        response.close = Mock()
        s.send = Mock(return_value=response)
        with self.assertRaisesRegex(ValueError, "Redirect blocked"):
            s.get("https://abc.web-security-academy.net/")
        self.assertEqual(s.send.call_count, 1)
        self.assertFalse(s.send.call_args.kwargs.get("allow_redirects", True))

    def test_pinned_session_rejects_other_lab_host(self):
        s = ScopedLabSession("abc.web-security-academy.net")
        with self.assertRaisesRegex(ValueError, "outside the selected"):
            s.get("https://other.web-security-academy.net/")


class AgentActionTests(unittest.TestCase):
    def test_parse_json_plan(self):
        raw = '{"hypothesis":"query param may control product lookup","actions":[{"method":"GET","path":"/product?productId=1","headers":{},"body":"","reason":"baseline","expected":"product page"}]}'
        hypothesis, plans = _parse_plan(raw)
        self.assertIn("product lookup", hypothesis)
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["action"].path, "/product?productId=1")
        self.assertEqual(plans[0]["expected"], "product page")

    def test_reject_invalid_method_absolute_and_extra_headers(self):
        cases = [
            '{"hypothesis":"x","actions":[{"method":"DELETE","path":"/account"}]}',
            '{"hypothesis":"x","actions":[{"method":"GET","path":"https://evil.example/"}]}',
            '{"hypothesis":"x","actions":[{"method":"GET","path":"/","headers":{"Host":"evil"}}]}',
            '{"hypothesis":"x","actions":[{"method":"GET","path":"//evil.example"}]}',
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                _, plans = _parse_plan(raw)
                self.assertEqual(plans, [])

    def test_observed_path_gate(self):
        surface = {"endpoints":["/filter"], "forms":[{"action":"/login"}]}
        self.assertTrue(_observed_path("/filter?category=x", surface))
        self.assertTrue(_observed_path("/login", surface))
        self.assertFalse(_observed_path("/admin-delete", surface))

    def test_observed_paths_include_script_calls(self):
        surface = {"endpoints":["/filter"], "forms":[],
                   "script_calls":[{"method":"POST","path":"/product/stock"}]}
        self.assertTrue(_observed_path("/product/stock", surface))
        self.assertFalse(_observed_path("/admin", surface))

    def test_waf_rejection_detection(self):
        self.assertTrue(_waf_rejected('"Attack detected"'))
        self.assertFalse(_waf_rejected('<html><body>ok</body></html>'))

    def test_agent_continues_after_waf_rejection(self):
        """The lab WAF saying 'Attack detected' must feed the next reasoning round,
        not terminate the loop after one action."""
        landing = '<html><title>Filter lab</title><a href="/product?productId=1">p</a></html>'
        product = ('<html><title>Product</title>'
                   '<script>req.open("POST","/product/stock",true);req.send(xml);</script></html>')

        class FakeResponse:
            def __init__(self, status, text):
                self.status_code = status
                self.text = text
                self.url = "https://abc123.web-security-academy.net/x"
                self.content = text.encode()
                self.headers = {"Content-Type": "text/html"}

        class FakeSession:
            def __init__(self, responses):
                self.responses = list(responses)
                self.calls = []
            def get(self, url, timeout=None, headers=None):
                self.calls.append(url)
                return self.responses.pop(0)
            def post(self, url, data=None, headers=None, timeout=None):
                self.calls.append(url)
                return self.responses.pop(0)

        fake = FakeSession([
            FakeResponse(200, landing),
            FakeResponse(200, product),
            FakeResponse(403, '"Attack detected"'),
            FakeResponse(403, '"Attack detected"'),
            FakeResponse(200, '<html><body>ok</body></html>'),
        ])

        def plan(body):
            return ('{"hypothesis":"probe stock endpoint","actions":[{"method":"POST",'
                    '"path":"/product/stock","headers":{"Content-Type":"application/xml"},'
                    f'"body":"{body}","reason":"test representation","expected":"stock data"}}]}}')

        plans = iter([plan("raw"), plan("alt1"), plan("alt2")])

        def fake_llm(**kwargs):
            try:
                return {"response": next(plans)}
            except StopIteration:
                return {"response": "1. Review the WAF rejection evidence in Burp."}

        with unittest.mock.patch.object(agentic_solver, "scoped_session", return_value=fake), \
             unittest.mock.patch("vapt_ai.call_ollama", side_effect=fake_llm):
            result = agentic_solver.agentic_solve(
                "https://abc123.web-security-academy.net/", allow_state_changes=True)

        # landing + product page + all three actions executed (no early break)
        self.assertEqual(len(fake.calls), 5)
        self.assertEqual(result.state, "attempted")
        self.assertIn("input filter", result.explanation)

    def test_duplicate_or_multiple_actions_rejected(self):
        _, plans = _parse_plan('{"hypothesis":"x","actions":[{"method":"GET","path":"/"},{"method":"GET","path":"/"}]}')
        self.assertEqual(plans, [])

    def test_state_change_requires_confirmation(self):
        self.assertFalse(_action_needs_confirmation(Action("GET", "/product?productId=1")))
        self.assertTrue(_action_needs_confirmation(Action("POST", "/product/stock")))
        self.assertTrue(_action_needs_confirmation(Action("GET", "/administrator-panel/delete?username=carlos")))

    def test_prompt_lookup_rejects_arbitrary_existing_path(self):
        with self.assertRaises(FileNotFoundError):
            find_template(str(ROOT / "README.md"))
        self.assertTrue(find_template("PS1").is_relative_to((ROOT / "prompts").resolve()))

    def test_specific_title_detected_before_generic_sqli(self):
        self.assertEqual(_detect("<title>SQL injection with filter bypass via XML encoding</title>"), "sqli_xml")

    def test_inspector_fetches_only_selected_url(self):
        class FakeResponse:
            status_code = 200
            url = "https://abc123.web-security-academy.net/"
            headers = {"Content-Type": "text/html"}
            text = '<html><title>Test</title><a href="/danger-get">danger</a><form action="/login"><input name="user"></form></html>'
            content = text.encode()

        class FakeSession:
            def __init__(self): self.calls = []
            def get(self, url, timeout): self.calls.append(url); return FakeResponse()

        fake = FakeSession()
        with unittest.mock.patch("lab_inspect.scoped_session", return_value=fake):
            result = inspect_lab("https://abc123.web-security-academy.net/")
        self.assertEqual(fake.calls, ["https://abc123.web-security-academy.net/"])
        self.assertEqual(result["pages_fetched"], 1)
        self.assertIn("/danger-get", result["pages"][0]["links"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
