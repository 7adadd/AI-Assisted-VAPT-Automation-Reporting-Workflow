#!/usr/bin/env python3
"""Playwright UI verification across all 5 tabs of the localhost VAPT Studio GUI."""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "deliverables" / "assets"
BASE = "http://127.0.0.1:8000"


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    console_errors = []
    page_errors = []
    external_requests = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("request", lambda req: external_requests.append(req.url) if not req.url.startswith(BASE) and not req.url.startswith("data:") else None)

        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(800)

        # Verify Tab 1: Dashboard
        ollama_txt = page.locator("#ollama-badge").inner_text()
        assert "Ollama Online" in ollama_txt, f"Unexpected Ollama badge: {ollama_txt}"
        assert page.locator("#challenges-tbody tr").count() == 12
        page.screenshot(path=str(ASSETS / "gui-preview-1-dashboard.png"))

        # Verify Tab 2: Analyzer (load sample + check dropdowns populated)
        page.click('button[data-tab="tab-analyzer"]')
        page.wait_for_timeout(300)
        assert page.locator("#an-template option").count() == 23
        page.select_option("#an-sample", "ps-01")
        page.screenshot(path=str(ASSETS / "gui-preview-2-analyzer.png"))

        # Verify Tab 3: Arena
        page.click('button[data-tab="tab-arena"]')
        page.wait_for_timeout(300)
        assert page.locator("#val-tbody tr").count() >= 24
        page.screenshot(path=str(ASSETS / "gui-preview-3-arena.png"))

        # Verify Tab 4: AD Graph
        page.click('button[data-tab="tab-graph"]')
        page.wait_for_timeout(700)
        canvas_cnt = page.locator("#cy canvas").count()
        assert canvas_cnt >= 1, "Cytoscape canvas not rendered"
        page.screenshot(path=str(ASSETS / "gui-preview-4-graph.png"))

        # Verify Tab 5: Report & Diff Studio + CVSS interaction
        page.click('button[data-tab="tab-studio"]')
        page.wait_for_timeout(500)
        page.select_option("#cvss-pr", "L")
        page.wait_for_timeout(400)
        cvss_txt = page.locator("#cvss-result").inner_text()
        assert "8.8 High" in cvss_txt, f"Unexpected CVSS result: {cvss_txt}"
        assert page.locator("#poc-gallery .poc-card").count() == 5
        page.screenshot(path=str(ASSETS / "gui-preview-5-reports.png"))

        browser.close()

    print("Console errors:", len(console_errors), console_errors)
    print("Page errors:", len(page_errors), page_errors)
    print("External requests:", len(external_requests), external_requests)
    assert len(console_errors) == 0, f"Console errors found: {console_errors}"
    assert len(page_errors) == 0, f"Page errors found: {page_errors}"
    assert len(external_requests) == 0, f"External requests found: {external_requests}"
    print("OK Playwright 5-tab verification passed with 0 errors and 0 external requests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
