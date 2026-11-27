#!/usr/bin/env python3
"""Launch the localhost-only AI-Assisted VAPT Automation Web GUI."""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    token = secrets.token_urlsafe(32)
    os.environ["VAPT_STUDIO_SESSION_TOKEN"] = token
    print("Starting AI-Assisted VAPT Automation Studio (Localhost & Privacy Only)")
    print("Dashboard URL: http://127.0.0.1:8000")
    print("Session token (required by local GUI): " + token)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
