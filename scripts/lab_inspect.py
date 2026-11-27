#!/usr/bin/env python3
"""Passive inspector for PortSwigger Web Security Academy lab instances.

Fetches real pages with GET only, extracts the observable attack surface
(forms, query parameters, endpoints, headers, scripts), and produces a
grounded HTTP context that the local model can actually analyse.

No payloads are sent. No exploitation. No POST/PUT/DELETE.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Dict, List
from urllib.parse import urljoin, urlparse

import requests
from safe_lab_http import scoped_session, validate_instance_url

ALLOWED_SUFFIXES = ("web-security-academy.net", "portswigger.net")


class _SurfaceParser(HTMLParser):
    """Collect forms, inputs, links and script sources from a page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: List[Dict[str, object]] = []
        self.links: List[str] = []
        self.scripts: List[str] = []
        self.text: List[str] = []
        self._form: Dict[str, object] | None = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        a = dict(attrs)
        if tag == "form":
            self._form = {"action": a.get("action", ""), "method": a.get("method", "GET").upper(), "inputs": []}
        elif tag in ("input", "textarea", "select") and self._form is not None:
            self._form["inputs"].append({
                "name": a.get("name", ""),
                "type": a.get("type", "text"),
                "value": a.get("value", "")[:120],
            })
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "script" and a.get("src"):
            self.scripts.append(a["src"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self._form is not None:
            self.forms.append(self._form)
            self._form = None

    def handle_data(self, data: str) -> None:
        t = data.strip()
        if t:
            self.text.append(t)


def _host_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in ALLOWED_SUFFIXES)


def inspect_lab(url: str, max_pages: int = 1, timeout: int = 12) -> Dict[str, object]:
    """Fetch only the caller-selected URL; never crawl arbitrary GET links."""
    origin, hostname = validate_instance_url(url)
    session = scoped_session(origin)
    parsed_url = urlparse(url)
    current = origin + (parsed_url.path or "/")
    if parsed_url.query:
        current += "?" + parsed_url.query
    pages: List[Dict[str, object]] = []
    try:
        r = session.get(current, timeout=min(timeout, 15))
    except Exception as exc:
        return {
            "origin": origin, "pages_fetched": 0, "query_params": [], "forms": [],
            "context": f"SOURCE: failed passive GET inspection\nERROR: {str(exc)[:150]}",
            "pages": [{"url": current, "error": str(exc)[:150]}],
        }

    html = r.text
    p = _SurfaceParser()
    try:
        p.feed(html)
    except Exception:
        pass
    params = sorted(set(re.findall(r"[?&]([A-Za-z0-9_.\-\[\]]+)\s*=", current)))
    pages.append({
        "url": current,
        "status": r.status_code,
        "headers": {k: v[:160] for k, v in r.headers.items()
                    if k.lower() in ("content-type", "server", "x-powered-by", "content-length")},
        "query_params": params,
        "forms": p.forms,
        "links": p.links[:25],
        "scripts": p.scripts[:15],
        "visible_text": " ".join(p.text)[:400],
    })

    # ---- build grounded context for the model ----
    lines = [
        "SOURCE: Passive GET inspection of a PortSwigger training lab instance.",
        "No payloads were sent. Every item below was observed in real responses.",
        "",
    ]
    for i, pg in enumerate(pages, 1):
        lines.append(f"[page {i}] {pg['url']}  status={pg.get('status', '?')}")
        if pg.get("error"):
            lines.append(f"  ERROR: {pg['error']}")
            continue
        if pg.get("query_params"):
            lines.append("  QUERY PARAMS: " + ", ".join(pg["query_params"]))
        for h, v in (pg.get("headers") or {}).items():
            lines.append(f"  HEADER {h}: {v}")
        for f in pg.get("forms", []):
            ins = ", ".join(f"{x['name']}({x['type']})" for x in f.get("inputs", []) if x.get("name"))
            lines.append(f"  FORM {f.get('method')} {f.get('action')} -> fields: {ins}")
        if pg.get("scripts"):
            lines.append("  SCRIPTS: " + ", ".join(pg["scripts"][:8]))
        if pg.get("visible_text"):
            lines.append(f"  TEXT: {pg['visible_text'][:180]}")
        lines.append("")

    context = "\n".join(lines)

    all_params = sorted({p for pg in pages for p in (pg.get("query_params") or [])})
    all_forms = [f for pg in pages for f in (pg.get("forms") or [])]

    return {
        "origin": origin,
        "pages_fetched": len(pages),
        "query_params": all_params,
        "forms": all_forms,
        "context": context,
        "pages": pages,
    }
