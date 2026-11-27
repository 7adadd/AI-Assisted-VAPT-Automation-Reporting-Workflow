"""Bounded HTTP transport for explicitly scoped PortSwigger training instances."""
from __future__ import annotations

from urllib.parse import urlsplit

import requests

ALLOWED_SUFFIX = ".web-security-academy.net"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 0
MAX_REQUESTS = 16
ALLOWED_AGENT_HEADERS = {"content-type", "accept", "referer"}


def validate_instance_url(url: str) -> tuple[str, str]:
    """Return canonical HTTPS origin and hostname; reject alternate ports/userinfo."""
    p = urlsplit(url)
    host = (p.hostname or "").lower().rstrip(".")
    if p.scheme.lower() != "https":
        raise ValueError("Only HTTPS PortSwigger lab instances are allowed")
    if not host.endswith(ALLOWED_SUFFIX) or host == ALLOWED_SUFFIX.lstrip("."):
        raise ValueError("Only a per-user *.web-security-academy.net lab instance is allowed")
    if p.username is not None or p.password is not None:
        raise ValueError("Credentials in lab URLs are not allowed")
    try:
        port = p.port
    except ValueError as exc:
        raise ValueError("Invalid port in lab URL") from exc
    if port not in (None, 443):
        raise ValueError("Only the standard HTTPS port 443 is allowed")
    return f"https://{host}", host


class ScopedLabSession(requests.Session):
    """A session pinned to one exact lab hostname, without redirect following."""

    def __init__(self, hostname: str, max_response_bytes: int = MAX_RESPONSE_BYTES):
        super().__init__()
        self._lab_hostname = hostname.lower()
        self._max_response_bytes = max_response_bytes
        self._request_count = 0
        self.headers.update({"User-Agent": "Mozilla/5.0 (compatible; VAPT-Studio/1.0; authorized-training-lab)"})

    def request(self, method, url, **kwargs):
        p = urlsplit(url)
        host = (p.hostname or "").lower().rstrip(".")
        if p.scheme.lower() != "https" or host != self._lab_hostname:
            raise ValueError("Request is outside the selected HTTPS lab origin")
        if p.username is not None or p.password is not None or p.port not in (None, 443):
            raise ValueError("Request contains disallowed URL authority data")
        method = method.upper()
        request_body = kwargs.get("data")
        if isinstance(request_body, (str, bytes)) and len(request_body) > 65536:
            raise ValueError("Request body exceeds the 64 KiB lab limit")
        if isinstance(request_body, dict) and sum(len(str(k)) + len(str(v)) for k, v in request_body.items()) > 65536:
            raise ValueError("Request body exceeds the 64 KiB lab limit")
        if self._request_count >= MAX_REQUESTS:
            raise ValueError("Per-run request limit reached")
        self._request_count += 1
        if method not in {"GET", "POST"}:
            raise ValueError(f"HTTP method {method} is not allowed")
        supplied_headers = kwargs.pop("headers", None) or {}
        if len(supplied_headers) > 8:
            raise ValueError("Too many request headers")
        safe_headers = {}
        for key, value in supplied_headers.items():
            if key.lower() not in ALLOWED_AGENT_HEADERS:
                raise ValueError(f"Header {key!r} is not allowed for lab requests")
            safe_headers[key] = value
        kwargs["headers"] = safe_headers
        kwargs["allow_redirects"] = False
        kwargs["stream"] = True
        timeout = kwargs.pop("timeout", 15)
        resp = super().request(method, url, timeout=timeout, **kwargs)
        if 300 <= resp.status_code < 400:
            location = resp.headers.get("Location", "")
            resp.close()
            raise ValueError(f"Redirect blocked by lab-origin policy: {location[:160]}")
        if resp.status_code in (401, 403, 404, 410, 429, 502, 503, 504):
            # Keep a small body for a useful blocked/expired/error classification.
            chunks = []
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    chunks.append(chunk)
                    if sum(map(len, chunks)) >= 4096:
                        break
            resp._content = b"".join(chunks)[:4096]
            resp._content_consumed = True
            return resp
        declared = resp.headers.get("Content-Length")
        if declared:
            try:
                if int(declared) > self._max_response_bytes:
                    resp.close()
                    raise ValueError("Lab response exceeds the configured size limit")
            except ValueError as exc:
                if "exceeds" in str(exc):
                    raise
        chunks, size = [], 0
        for chunk in resp.iter_content(chunk_size=16384):
            if not chunk:
                continue
            size += len(chunk)
            if size > self._max_response_bytes:
                resp.close()
                raise ValueError("Lab response exceeds the configured size limit")
            chunks.append(chunk)
        resp._content = b"".join(chunks)
        resp._content_consumed = True
        return resp


def scoped_session(origin_or_url: str) -> ScopedLabSession:
    _, hostname = validate_instance_url(origin_or_url)
    return ScopedLabSession(hostname)
