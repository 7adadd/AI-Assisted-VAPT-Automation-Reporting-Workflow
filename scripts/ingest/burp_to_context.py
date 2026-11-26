#!/usr/bin/env python3
"""Parse raw HTTP request/response text into line-cited [http:line N] LLM context."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def format_http_context(raw_text: str, max_lines: int = 180) -> str:
    out = []
    for idx, line in enumerate(raw_text.splitlines(), start=1):
        out.append(f"[http:line {idx}] {line.rstrip()}")
        if len(out) >= max_lines:
            out.append(f"[http:truncated] stopped at {max_lines} lines")
            break
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert raw HTTP request/response to line-cited context.")
    ap.add_argument("http_file", help="Path to raw HTTP file")
    ap.add_argument("--out", help="Output text file path")
    ap.add_argument("--max-lines", type=int, default=180)
    args = ap.parse_args()

    raw = Path(args.http_file).read_text(encoding="utf-8", errors="replace")
    ctx = format_http_context(raw, max_lines=args.max_lines)
    if args.out:
        op = Path(args.out)
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(ctx, encoding="utf-8")
        print(f"OK wrote {op}")
    else:
        print(ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
