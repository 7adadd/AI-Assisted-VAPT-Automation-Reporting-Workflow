#!/usr/bin/env python3
"""Read-only Nmap XML open-port verifier.

Generated via prompt AD3 (qwen2.5:3b) in ai-AD3-nmap-py.md.
Human L2 QA fixes logged in evidence/validation-log.md:
  - Raw AI checked `port.get('state') == 'open'` (wrong: state is in child `<state state='open'/>`).
  - Raw AI checked `host.get('host_name')` (wrong: IP is in child `<address addr='...'/>`).
  - Raw AI accessed `.get('product')` without null-checking `<service>` or missing attributes.
"""
from __future__ import annotations

import json
import sys
from xml.etree import ElementTree as ET


def parse_nmap_xml(xml_file: str) -> list[dict]:
    tree = ET.parse(xml_file)
    root = tree.getroot()
    open_ports: list[dict] = []
    for host in root.findall(".//host"):
        addr_el = host.find("address")
        ip = addr_el.get("addr", "unknown") if addr_el is not None else "unknown"
        for port in host.findall(".//port"):
            st_el = port.find("state")
            if st_el is not None and st_el.get("state") == "open":
                svc_el = port.find("service")
                svc_name = svc_el.get("name", "unknown") if svc_el is not None else "unknown"
                product = svc_el.get("product", "") if svc_el is not None else ""
                version = svc_el.get("version", "") if svc_el is not None else ""
                ver_full = " ".join(x for x in (product, version) if x).strip() or "unspecified"
                open_ports.append({
                    "ip": ip,
                    "port": f"{port.get('portid')}/{port.get('protocol', 'tcp')}",
                    "service": svc_name,
                    "version": ver_full,
                })
    return open_ports


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python nmap_triage_verifier.py <nmap_xml_file>")
        return 1
    ports = parse_nmap_xml(sys.argv[1])
    print(json.dumps(ports, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
