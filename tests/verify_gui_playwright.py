#!/usr/bin/env python3
"""Playwright smoke test for the current sidebar GUI. Screenshots are opt-in."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "deliverables" / "assets"
BASE = "http://127.0.0.1:8000"
SAVE_SHOTS = os.environ.get("VAPT_TEST_SCREENSHOTS") == "1"


def main() -> int:
    if SAVE_SHOTS:
        ASSETS.mkdir(parents=True, exist_ok=True)
    console_errors, page_errors, external_requests, bad_responses = [], [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on("request", lambda r: external_requests.append(r.url) if not r.url.startswith(BASE) and not r.url.startswith("data:") else None)
        page.on("response", lambda r: bad_responses.append((r.status, r.url)) if r.status >= 400 else None)
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(600)
        assert page.title().startswith("VAPT Studio")
        expected = ["analyzer", "solver", "dashboard", "graph", "reports"]
        assert page.locator(".nav-btn").count() == len(expected)
        for view in expected:
            page.click(f'.nav-btn[data-view="{view}"]')
            assert page.locator(f"#view-{view}.active").count() == 1
            if view == "solver":
                assert page.locator("#solve-url").count() == 1
                assert page.locator("#solve-desc").count() == 1
                assert not page.locator("#solve-consent").is_checked()
            if SAVE_SHOTS:
                page.screenshot(path=str(ASSETS / f"gui-smoke-{view}.png"))
        # Validate inline empty-input feedback and that no stale verdict can be logged.
        page.click('.nav-btn[data-view="analyzer"]')
        page.click("#btn-run")
        assert page.locator("#verdict-row").is_hidden()
        assert page.locator("#result-hint").inner_text()
        browser.close()
    assert not console_errors, console_errors
    assert not page_errors, page_errors
    assert not external_requests, external_requests
    assert not bad_responses, bad_responses
    print("PASS GUI views; no JS/console/HTTP/external-request errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
