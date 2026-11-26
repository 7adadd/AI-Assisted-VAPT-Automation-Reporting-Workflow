#!/usr/bin/env python3
"""Parse jadx AndroidManifest.xml or decompiled Java files into line-cited LLM context."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def format_mobile_context(file_path: Path, start_line: int = 1, end_line: int = 250) -> str:
    tag = "manifest" if file_path.name.lower() == "androidmanifest.xml" else f"jadx:{file_path.name}"
    lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    out = []
    for idx in range(max(1, start_line), min(len(lines), end_line) + 1):
        out.append(f"[{tag}:{idx}] {lines[idx - 1].rstrip()}")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert AndroidManifest.xml or jadx Java file to line-cited context.")
    ap.add_argument("source_file", help="Path to AndroidManifest.xml or .java file")
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=250)
    ap.add_argument("--out", help="Output text file path")
    args = ap.parse_args()

    ctx = format_mobile_context(Path(args.source_file), start_line=args.start, end_line=args.end)
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
