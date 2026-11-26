#!/usr/bin/env python3
"""Parse enum4linux / SMB / LDAP / banner enumeration text into line-cited context."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def format_enum_context(raw_text: str, max_lines: int = 250) -> str:
    out_lines = []
    for idx, line in enumerate(raw_text.splitlines(), start=1):
        stripped = line.rstrip()
        if not stripped:
            continue
        out_lines.append(f"[enum:line {idx}] {stripped}")
        if len(out_lines) >= max_lines:
            out_lines.append(f"[enum:truncated] stopped at {max_lines} non-empty lines")
            break
    return "\n".join(out_lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert enumeration text output to line-cited LLM context.")
    ap.add_argument("enum_file", help="Path to raw enumeration output file")
    ap.add_argument("--out", help="Output text file path")
    ap.add_argument("--max-lines", type=int, default=250)
    args = ap.parse_args()

    raw = Path(args.enum_file).read_text(encoding="utf-8", errors="replace")
    ctx = format_enum_context(raw, max_lines=args.max_lines)
    if args.out:
        out_p = Path(args.out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(ctx, encoding="utf-8")
        print(f"OK wrote {out_p}")
    else:
        print(ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
