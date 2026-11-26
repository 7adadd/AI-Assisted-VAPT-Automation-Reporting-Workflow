#!/usr/bin/env python3
"""Parse BloodHound JSON graph into LLM edge context + exact BFS shortest-path ground truth."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def load_bloodhound(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


ATTACK_RIGHTS = {
    "GenericAll",
    "WriteDacl",
    "WriteOwner",
    "ForceChangePassword",
    "GetChangesAll",
    "GetChanges",
    "MemberOf",
    "AddMember",
    "GenericWrite",
    "WriteAccountRestrictions",
    "AllowedToDelegate",
    "AdminTo",
    "HasSession",
}


def shortest_path_bfs(
    edges: List[Dict],
    start: str,
    targets: set[str],
) -> Optional[List[Dict]]:
    adj = defaultdict(list)
    for e in edges:
        if e.get("right") in ATTACK_RIGHTS:
            adj[e["source"]].append(e)

    q = deque([(start, [])])
    visited = {start}
    while q:
        node, path = q.popleft()
        if node in targets and path:
            return path
        for edge in adj.get(node, []):
            nxt = edge["target"]
            if nxt not in visited:
                visited.add(nxt)
                q.append((nxt, path + [edge]))
    return None


def compute_ground_truth(data: Dict) -> Dict:
    nodes = {n["id"]: n for n in data.get("nodes", [])}
    edges = data.get("edges", [])
    high_value = {
        n["id"]
        for n in data.get("nodes", [])
        if n.get("highvalue") or "DOMAIN ADMINS" in n["id"].upper() or n.get("type") == "Domain"
    }

    paths = {}
    for n in data.get("nodes", []):
        if n.get("type") == "User" and not n.get("highvalue"):
            p = shortest_path_bfs(edges, n["id"], high_value)
            if p:
                paths[n["id"]] = [
                    {
                        "id": e["id"],
                        "source": e["source"],
                        "right": e["right"],
                        "target": e["target"],
                    }
                    for e in p
                ]
            else:
                paths[n["id"]] = None

    return {"domain": data.get("domain", "LAB.LOCAL"), "node_count": len(nodes), "edge_count": len(edges), "paths_to_highvalue": paths}


def format_edges_context(data: Dict) -> str:
    lines = [f"[bh:domain] {data.get('domain', 'LAB.LOCAL')}", ""]
    lines.append("=== PRINCIPALS ===")
    for n in data.get("nodes", []):
        flags = []
        if n.get("kerberoastable"):
            flags.append(f"SPN={n.get('spn')}")
        if n.get("asrep_roastable"):
            flags.append("DONT_REQ_PREAUTH=true")
        if n.get("highvalue"):
            flags.append("HIGH_VALUE=true")
        if n.get("description"):
            flags.append(f"desc=\"{n['description']}\"")
        flag_str = " | ".join(flags) if flags else "standard"
        lines.append(f"[bh:node {n['id']}] type={n.get('type')} {flag_str}")

    lines.append("")
    lines.append("=== EDGES ===")
    for e in data.get("edges", []):
        lines.append(
            f"[bh:edge {e['id']}] {e['source']} --({e['right']})--> {e['target']} "
            f"[isACL={e.get('is_acl', False)}]"
        )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert BloodHound JSON to LLM context & BFS ground truth.")
    ap.add_argument("bh_json", help="Path to BloodHound lab JSON")
    ap.add_argument("--out", help="Output context text file")
    ap.add_argument("--ground-truth-out", help="Output ground truth JSON path")
    args = ap.parse_args()

    data = load_bloodhound(Path(args.bh_json))
    ctx = format_edges_context(data)
    gt = compute_ground_truth(data)

    if args.out:
        op = Path(args.out)
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(ctx, encoding="utf-8")
        print(f"OK wrote {op}")
    else:
        print(ctx)

    if args.ground_truth_out:
        gp = Path(args.ground_truth_out)
        gp.parent.mkdir(parents=True, exist_ok=True)
        gp.write_text(json.dumps(gt, indent=2), encoding="utf-8")
        print(f"OK wrote {gp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
