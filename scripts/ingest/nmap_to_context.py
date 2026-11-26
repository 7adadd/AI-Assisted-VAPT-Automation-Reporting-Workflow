#!/usr/bin/env python3
"""Parse Nmap XML (-oX / -oA) into grounded, citation-tagged LLM context."""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List


def parse_nmap_xml(xml_path: Path) -> Dict:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    hosts_data: List[Dict] = []

    for host in root.findall("host"):
        status_el = host.find("status")
        state = status_el.attrib.get("state", "unknown") if status_el is not None else "unknown"
        addr_el = host.find("address")
        addr = addr_el.attrib.get("addr", "unknown") if addr_el is not None else "unknown"

        ports_list: List[Dict] = []
        ports_el = host.find("ports")
        if ports_el is not None:
            for port in ports_el.findall("port"):
                proto = port.attrib.get("protocol", "tcp")
                portid = port.attrib.get("portid", "?")
                st_el = port.find("state")
                p_state = st_el.attrib.get("state", "unknown") if st_el is not None else "unknown"
                svc_el = port.find("service")
                svc_name = svc_el.attrib.get("name", "unknown") if svc_el is not None else "unknown"
                product = svc_el.attrib.get("product", "") if svc_el is not None else ""
                version = svc_el.attrib.get("version", "") if svc_el is not None else ""
                extrainfo = svc_el.attrib.get("extrainfo", "") if svc_el is not None else ""
                ver_str = " ".join(x for x in [product, version, extrainfo] if x).strip() or "unspecified"

                scripts = []
                for sc in port.findall("script"):
                    scripts.append({
                        "id": sc.attrib.get("id", ""),
                        "output": " ".join((sc.attrib.get("output", "") or "").split())[:300],
                    })

                ports_list.append({
                    "port": portid,
                    "proto": proto,
                    "state": p_state,
                    "service": svc_name,
                    "version": ver_str,
                    "scripts": scripts,
                })

        hosts_data.append({"address": addr, "state": state, "ports": ports_list})

    return {
        "scanner": root.attrib.get("scanner", "nmap"),
        "args": root.attrib.get("args", ""),
        "hosts": hosts_data,
    }


def format_context(data: Dict) -> str:
    lines = [
        f"[nmap:args] {data['args']}",
        "",
    ]
    for h in data["hosts"]:
        lines.append(f"[nmap:host {h['address']}] state={h['state']}")
        for p in h["ports"]:
            cite = f"[nmap:port {p['port']}/{p['proto']}]"
            lines.append(f"{cite} state={p['state']} service={p['service']} version=\"{p['version']}\"")
            for sc in p["scripts"]:
                lines.append(f"  {cite}[script:{sc['id']}] {sc['output']}")
        lines.append("")
    return "\n".join(lines).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert Nmap XML to grounded LLM context.")
    ap.add_argument("xml_file", help="Path to Nmap XML file")
    ap.add_argument("--out", help="Output text file path")
    ap.add_argument("--json-out", help="Optional structured JSON output path")
    args = ap.parse_args()

    data = parse_nmap_xml(Path(args.xml_file))
    ctx = format_context(data)
    if args.out:
        out_p = Path(args.out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(ctx, encoding="utf-8")
        print(f"OK wrote {out_p}")
    else:
        print(ctx)

    if args.json_out:
        jp = Path(args.json_out)
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"OK wrote {jp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
