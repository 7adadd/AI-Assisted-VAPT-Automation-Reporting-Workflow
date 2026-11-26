#!/usr/bin/env python3
"""Deterministic word-level and line-level diff between AI draft and human-edited VAPT reports."""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path


def tokenize_words(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def analyze_diff(ai_text: str, human_text: str) -> dict:
    ai_lines = ai_text.splitlines()
    hu_lines = human_text.splitlines()
    ai_words = tokenize_words(ai_text)
    hu_words = tokenize_words(human_text)

    word_sm = difflib.SequenceMatcher(None, ai_words, hu_words)
    line_sm = difflib.SequenceMatcher(None, ai_lines, hu_lines)

    added_words = 0
    removed_words = 0
    replaced_ai_words = 0
    replaced_hu_words = 0
    for tag, i1, i2, j1, j2 in word_sm.get_opcodes():
        if tag == "insert":
            added_words += (j2 - j1)
        elif tag == "delete":
            removed_words += (i2 - i1)
        elif tag == "replace":
            replaced_ai_words += (i2 - i1)
            replaced_hu_words += (j2 - j1)

    unified = list(
        difflib.unified_diff(
            ai_lines,
            hu_lines,
            fromfile="vapt-report-ai-draft.md",
            tofile="vapt-report-human-edited.md",
            lineterm="",
            n=2,
        )
    )

    return {
        "ai_lines": len(ai_lines),
        "human_lines": len(hu_lines),
        "ai_words": len(ai_words),
        "human_words": len(hu_words),
        "word_similarity_pct": round(word_sm.ratio() * 100, 1),
        "line_similarity_pct": round(line_sm.ratio() * 100, 1),
        "added_words": added_words,
        "removed_words": removed_words,
        "replaced_ai_words": replaced_ai_words,
        "replaced_human_words": replaced_hu_words,
        "unified_diff": "\n".join(unified),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute AI-draft vs human-edited diff metrics.")
    ap.add_argument("ai_draft", help="Path to AI draft markdown")
    ap.add_argument("human_edited", help="Path to human-edited markdown")
    ap.add_argument("--out", help="Optional output markdown summary path")
    args = ap.parse_args()

    ai_text = Path(args.ai_draft).read_text(encoding="utf-8")
    hu_text = Path(args.human_edited).read_text(encoding="utf-8")
    stats = analyze_diff(ai_text, hu_text)

    md = [
        "# AI Draft vs. Human-Edited Report — Deterministic Diff Metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| AI Draft length | {stats['ai_lines']} lines / {stats['ai_words']} words |",
        f"| Human-Edited length | {stats['human_lines']} lines / {stats['human_words']} words |",
        f"| Word-level similarity | {stats['word_similarity_pct']}% |",
        f"| Line-level similarity | {stats['line_similarity_pct']}% |",
        f"| Words purely inserted | {stats['added_words']} |",
        f"| Words purely deleted | {stats['removed_words']} |",
        f"| Words replaced (AI -> Human) | {stats['replaced_ai_words']} -> {stats['replaced_human_words']} |",
        "",
        "## Unified Diff Excerpt",
        "```diff",
        stats["unified_diff"][:12000],
        "```",
    ]
    out_str = "\n".join(md)
    if args.out:
        op = Path(args.out)
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(out_str, encoding="utf-8")
        print(f"OK wrote diff metrics -> {op}")
    else:
        print(out_str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
