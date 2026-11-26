#!/usr/bin/env python3
"""Read-only BloodHound lab JSON security auditor.

Generated via prompt AD3 (qwen2.5:3b) in ai-AD3-bh-py.md.
Human L2 QA fixes logged in evidence/validation-log.md:
  - Raw AI assumed keys `users`, `Kerberoastable`, `Type=='DCSync'` instead of actual
    schema (`nodes`, `edges`, `kerberoastable`, `asrep_roastable`, `right`).
  - Raw AI combined rights with `and` instead of membership in a set.
"""
from __future__ import annotations

import json
import sys

DANGEROUS_RIGHTS = {"GenericAll", "WriteDacl", "WriteOwner", "ForceChangePassword", "GetChangesAll", "GetChanges"}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python bh_path_auditor.py <bloodhound_json>")
        return 1

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)

    kerb = [n["id"] for n in data.get("nodes", []) if n.get("kerberoastable")]
    asrep = [n["id"] for n in data.get("nodes", []) if n.get("asrep_roastable")]
    edges = [
        f"[{e['id']}] {e['source']} --({e['right']})--> {e['target']}"
        for e in data.get("edges", [])
        if e.get("right") in DANGEROUS_RIGHTS
    ]

    print("Kerberoastable Users:", ", ".join(kerb) or "None")
    print("AS-REP Roastable Users:", ", ".join(asrep) or "None")
    print("Dangerous ACL / Replication Edges:")
    for line in edges:
        print(" ", line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
