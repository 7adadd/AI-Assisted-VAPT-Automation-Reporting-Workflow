#!/usr/bin/env python3
"""Exact CVSS v3.1 Base Score calculator and vector validator (FIRST.org spec)."""
from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Dict, Tuple

WEIGHTS = {
    "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20},
    "AC": {"L": 0.77, "H": 0.44},
    "PR_U": {"N": 0.85, "L": 0.62, "H": 0.27},
    "PR_C": {"N": 0.85, "L": 0.68, "H": 0.50},
    "UI": {"N": 0.85, "R": 0.62},
    "C": {"H": 0.56, "L": 0.22, "N": 0.0},
    "I": {"H": 0.56, "L": 0.22, "N": 0.0},
    "A": {"H": 0.56, "L": 0.22, "N": 0.0},
}


def roundup(x: float) -> float:
    return math.ceil(round(x * 100000) / 10000.0) / 10.0


def parse_vector(vector: str) -> Dict[str, str]:
    parts = vector.strip().split("/")
    if not parts or parts[0] != "CVSS:3.1":
        raise ValueError(f"Invalid CVSS 3.1 prefix in vector: {vector!r}")
    metrics: Dict[str, str] = {}
    for item in parts[1:]:
        if ":" not in item:
            raise ValueError(f"Malformed metric token: {item!r}")
        k, v = item.split(":", 1)
        metrics[k] = v
    required = ["AV", "AC", "PR", "UI", "S", "C", "I", "A"]
    missing = [r for r in required if r not in metrics]
    if missing:
        raise ValueError(f"Missing required CVSS 3.1 metrics: {missing}")
    return metrics


def score_vector(vector: str) -> Tuple[float, str, Dict]:
    m = parse_vector(vector)
    scope = m["S"]
    if scope not in ("U", "C"):
        raise ValueError(f"Invalid Scope value: {scope}")

    av = WEIGHTS["AV"][m["AV"]]
    ac = WEIGHTS["AC"][m["AC"]]
    pr = (WEIGHTS["PR_C"] if scope == "C" else WEIGHTS["PR_U"])[m["PR"]]
    ui = WEIGHTS["UI"][m["UI"]]
    c = WEIGHTS["C"][m["C"]]
    i = WEIGHTS["I"][m["I"]]
    a = WEIGHTS["A"][m["A"]]

    iss = 1.0 - ((1.0 - c) * (1.0 - i) * (1.0 - a))
    if scope == "U":
        impact = 6.42 * iss
    else:
        impact = 7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02) ** 15)

    exploitability = 8.22 * av * ac * pr * ui

    if impact <= 0:
        base = 0.0
    elif scope == "U":
        base = roundup(min(impact + exploitability, 10.0))
    else:
        base = roundup(min(1.08 * (impact + exploitability), 10.0))

    if base == 0.0:
        sev = "None"
    elif base <= 3.9:
        sev = "Low"
    elif base <= 6.9:
        sev = "Medium"
    elif base <= 8.9:
        sev = "High"
    else:
        sev = "Critical"

    return base, sev, {"vector": vector, "base_score": base, "severity": sev, "iss": round(iss, 4), "impact": round(impact, 4), "exploitability": round(exploitability, 4)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute exact CVSS v3.1 Base Score.")
    ap.add_argument("vectors", nargs="+", help="One or more CVSS:3.1/... strings")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    out = []
    for vec in args.vectors:
        base, sev, detail = score_vector(vec)
        out.append(detail)
        if not args.json:
            print(f"{vec} -> {base:.1f} ({sev})")
    if args.json:
        print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
