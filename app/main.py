#!/usr/bin/env python3
"""Localhost-only FastAPI backend for the AI-Assisted VAPT Automation Web GUI."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR / "ingest"))
sys.path.insert(0, str(SCRIPTS_DIR / "reporting"))

from vapt_ai import (  # noqa: E402
    DEFAULT_OLLAMA_URL,
    call_ollama,
    find_template,
    parse_prompt_template,
    render_prompt,
    validate_local_url,
)
from nmap_to_context import format_context as format_nmap_ctx, parse_nmap_xml  # noqa: E402
from enum_to_context import format_enum_context  # noqa: E402
from bloodhound_to_context import (  # noqa: E402
    compute_ground_truth,
    format_edges_context,
    load_bloodhound,
)
from burp_to_context import format_http_context  # noqa: E402
from mobile_to_context import format_mobile_context  # noqa: E402
from calc_cvss import score_vector  # noqa: E402
from diff_draft import analyze_diff  # noqa: E402

STATIC_DIR = ROOT / "app" / "static"
DELIVERABLES_DIR = ROOT / "deliverables"
PROMPTS_DIR = ROOT / "prompts"
VALIDATION_LOG = DELIVERABLES_DIR / "validation-log.md"
EVIDENCE_LOG = ROOT / "evidence" / "validation-log.md"
BENCHMARKS_MD = ROOT / "lab" / "model-benchmarks.md"
CHALLENGE_EVAL_JSON = DELIVERABLES_DIR / "challenge-evaluation.json"
BH_LAB_JSON = ROOT / "lab" / "ad-lab-dataset" / "bloodhound_lab.json"

app = FastAPI(
    title="AI-Assisted VAPT Automation Studio",
    description="Localhost-only passive VAPT analysis, validation, and reporting dashboard",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
if DELIVERABLES_DIR.exists():
    app.mount("/deliverables", StaticFiles(directory=str(DELIVERABLES_DIR)), name="deliverables")


CHALLENGE_CATALOG: List[Dict[str, str]] = [
    {"id": "dvwa-01", "suite": "DVWA", "name": "SQL Injection (UNION)", "path": "lab/challenge-samples/dvwa/dvwa-01-sqli-union.http", "artifact_type": "http", "recommended_template": "W1", "target_param": "id", "expected_vuln": "SQL Injection"},
    {"id": "dvwa-02", "suite": "DVWA", "name": "Reflected XSS", "path": "lab/challenge-samples/dvwa/dvwa-02-xss-reflected.http", "artifact_type": "http", "recommended_template": "W1", "target_param": "name", "expected_vuln": "Cross-Site Scripting"},
    {"id": "dvwa-03", "suite": "DVWA", "name": "Stored XSS", "path": "lab/challenge-samples/dvwa/dvwa-03-xss-stored.http", "artifact_type": "http", "recommended_template": "W1", "target_param": "mtxMessage", "expected_vuln": "Cross-Site Scripting"},
    {"id": "dvwa-04", "suite": "DVWA", "name": "OS Command Injection", "path": "lab/challenge-samples/dvwa/dvwa-04-cmdi-ping.http", "artifact_type": "http", "recommended_template": "W1", "target_param": "ip", "expected_vuln": "Command Injection"},
    {"id": "dvwa-05", "suite": "DVWA", "name": "Local File Inclusion", "path": "lab/challenge-samples/dvwa/dvwa-05-lfi-traversal.http", "artifact_type": "http", "recommended_template": "W1", "target_param": "page", "expected_vuln": "Path Traversal / File Inclusion"},
    {"id": "dvwa-06", "suite": "DVWA", "name": "CSRF Password Change", "path": "lab/challenge-samples/dvwa/dvwa-06-csrf-password.http", "artifact_type": "http", "recommended_template": "W1", "target_param": "password_new", "expected_vuln": "Cross-Site Request Forgery"},
    {"id": "ps-01", "suite": "PortSwigger", "name": "SSRF Stock Check", "path": "lab/challenge-samples/portswigger/ps-01-ssrf-stock-check.http", "artifact_type": "http", "recommended_template": "W1", "target_param": "stockApi", "expected_vuln": "Server-Side Request Forgery (SSRF)"},
    {"id": "ps-02", "suite": "PortSwigger", "name": "XXE External Entity", "path": "lab/challenge-samples/portswigger/ps-02-xxe-product-xml.http", "artifact_type": "http", "recommended_template": "W1", "target_param": "productId", "expected_vuln": "XML External Entity (XXE)"},
    {"id": "ps-03", "suite": "PortSwigger", "name": "SSTI Template Injection", "path": "lab/challenge-samples/portswigger/ps-03-ssti-greeting.http", "artifact_type": "http", "recommended_template": "W1", "target_param": "message", "expected_vuln": "Server-Side Template Injection (SSTI)"},
    {"id": "ps-04", "suite": "PortSwigger", "name": "IDOR Account Exposure", "path": "lab/challenge-samples/portswigger/ps-04-idor-account-export.http", "artifact_type": "http", "recommended_template": "W1", "target_param": "id", "expected_vuln": "Insecure Direct Object Reference (IDOR)"},
    {"id": "ps-05", "suite": "PortSwigger", "name": "JWT Unverified Signature (alg=none)", "path": "lab/challenge-samples/portswigger/ps-05-jwt-unverified-signature.http", "artifact_type": "http", "recommended_template": "W1", "target_param": "session", "expected_vuln": "Broken Authentication / JWT Flaw"},
    {"id": "ps-06", "suite": "PortSwigger", "name": "Error-Based SQLi in Cookie", "path": "lab/challenge-samples/portswigger/ps-06-sqli-blind-tracking-cookie.http", "artifact_type": "http", "recommended_template": "W1", "target_param": "TrackingId", "expected_vuln": "SQL Injection"},
]

EXTRA_SAMPLES: List[Dict[str, str]] = [
    {"id": "lab-nmap", "suite": "Lab Recon", "name": "Kali WSL Nmap Scan (XML)", "path": "evidence/week2/nmap-lab.xml", "artifact_type": "nmap", "recommended_template": "R1"},
    {"id": "lab-enum", "suite": "Lab AD", "name": "AD enum4linux-ng Output", "path": "lab/ad-lab-dataset/enum4linux_lab.txt", "artifact_type": "enum", "recommended_template": "AD4"},
    {"id": "lab-bh", "suite": "Lab AD", "name": "BloodHound LAB.LOCAL Graph (JSON)", "path": "lab/ad-lab-dataset/bloodhound_lab.json", "artifact_type": "bloodhound", "recommended_template": "AD1"},
    {"id": "lab-acl", "suite": "Lab AD", "name": "AD ACL Dump", "path": "lab/ad-lab-dataset/acl_dump.txt", "artifact_type": "raw", "recommended_template": "AD2"},
    {"id": "lab-diva-java", "suite": "Mobile DIVA", "name": "DIVA HardcodeActivity.java", "path": "evidence/week3/diva-src/sources/jakhar/aseem/diva/HardcodeActivity.java", "artifact_type": "mobile", "recommended_template": "M1"},
    {"id": "lab-diva-manifest", "suite": "Mobile DIVA", "name": "DIVA AndroidManifest.xml", "path": "evidence/week3/diva-src/resources/AndroidManifest.xml", "artifact_type": "mobile", "recommended_template": "M3"},
]


def _all_samples_map() -> Dict[str, Dict[str, str]]:
    return {item["id"]: item for item in (CHALLENGE_CATALOG + EXTRA_SAMPLES)}


def _parse_validation_log() -> Dict[str, Any]:
    path = VALIDATION_LOG if VALIDATION_LOG.exists() else EVIDENCE_LOG
    entries: List[Dict[str, str]] = []
    verified = 0
    partial = 0
    hallucinated = 0
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|"):
                continue
            cols = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cols) < 8 or cols[0] in ("ID", "---") or set(cols[0]) <= {"-"}:
                continue
            verdict = cols[7]
            if "✅" in verdict or "Verified" in verdict:
                verified += 1
                norm = "Verified"
            elif "❌" in verdict or "Hallucination" in verdict:
                hallucinated += 1
                norm = "Hallucination"
            else:
                partial += 1
                norm = "Corrected"
            entries.append({
                "id": cols[0],
                "phase": cols[1],
                "claim": cols[2],
                "model": cols[3],
                "source": cols[4],
                "check": cols[5],
                "result": cols[6],
                "verdict": verdict,
                "status": norm,
            })
    total = len(entries)
    acc_pct = round((verified / total) * 100, 1) if total else 0.0
    usable_pct = round(((verified + partial) / total) * 100, 1) if total else 0.0
    hall_pct = round((hallucinated / total) * 100, 1) if total else 0.0
    return {
        "total": total,
        "verified": verified,
        "corrected": partial,
        "hallucinated": hallucinated,
        "accuracy_pct": acc_pct,
        "usable_pct": usable_pct,
        "hallucination_pct": hall_pct,
        "entries": entries,
    }


def _ingest_artifact(raw_text: str, filename: str, artifact_type: str) -> str:
    atype = (artifact_type or "auto").lower()
    fname = (filename or "artifact.txt").lower()
    if atype == "auto":
        if fname.endswith(".xml") and "androidmanifest" not in fname:
            atype = "nmap"
        elif fname.endswith(".json"):
            atype = "bloodhound"
        elif fname.endswith(".java") or "manifest" in fname:
            atype = "mobile"
        elif fname.endswith(".http") or raw_text.lstrip().startswith(("GET ", "POST ", "PUT ", "DELETE ", "HTTP/")):
            atype = "http"
        else:
            atype = "enum"

    if atype == "nmap":
        with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8") as tmp:
            tmp.write(raw_text)
            tmp_path = Path(tmp.name)
        try:
            return format_nmap_ctx(parse_nmap_xml(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)
    if atype == "bloodhound":
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp.write(raw_text)
            tmp_path = Path(tmp.name)
        try:
            return format_edges_context(load_bloodhound(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)
    if atype == "http":
        return format_http_context(raw_text)
    if atype == "mobile":
        suffix = Path(filename or "Source.java").name
        with tempfile.TemporaryDirectory() as td:
            fp = Path(td) / suffix
            fp.write_text(raw_text, encoding="utf-8")
            return format_mobile_context(fp)
    if atype == "enum":
        return format_enum_context(raw_text)
    return raw_text


def _build_template_vars(tpl_text: str, ingested: str, extra_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    placeholders = re.findall(r"\{\{([^}]+)\}\}", tpl_text)
    defaults = {
        "target_user": "m.ali@LAB.LOCAL and j.smith@LAB.LOCAL",
        "objective": "Audit read-only security posture",
        "domain": "LAB.LOCAL",
        "language": "PowerShell",
        "spn_list": ingested,
        "asrep_list": ingested,
        "vuln_class": "Input Validation / Injection",
        "constraints": "Non-destructive lab PoC only, <= 60 chars",
        "class_purpose": "Decompiled Android security review",
        "bypass_goal": "Inspect or bypass security check in lab",
        "app_package": "jakhar.aseem.diva",
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",
        "engagement_context": "Isolated DEPI Project 5 Lab Environment",
        "all_findings_table": ingested,
        "findings_with_cvss": ingested,
    }
    variables: Dict[str, str] = {}
    for ph in placeholders:
        k = ph.strip()
        if extra_vars and k in extra_vars and extra_vars[k]:
            variables[k] = extra_vars[k]
        elif k in defaults and k not in (
            "nmap_xml_summary", "service_banner_block", "all_recon_outputs", "recon_findings_json",
            "bloodhound_edges_json", "acl_dump", "enum4linux_output", "http_request", "request_context",
            "http_response", "validated_poc_notes", "candidate_payloads", "java_source_block",
            "target_class_context", "android_manifest_xml", "suspected_issue", "validated_finding_notes",
            "finding_summary",
        ):
            variables[k] = defaults[k]
        else:
            variables[k] = ingested
    return variables


@app.get("/")
def serve_index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/health")
def api_health() -> Dict[str, Any]:
    url = validate_local_url(DEFAULT_OLLAMA_URL)
    ollama_ok = False
    models: List[str] = []
    err = None
    try:
        r = requests.get(f"{url}/api/tags", timeout=3)
        r.raise_for_status()
        models = [m.get("name", "") for m in r.json().get("models", [])]
        ollama_ok = True
    except Exception as exc:
        err = str(exc)

    vstats = _parse_validation_log()
    prompt_files = [p for p in PROMPTS_DIR.rglob("*.md") if p.name != ".gitkeep"]
    return {
        "status": "ok",
        "privacy_mode": "127.0.0.1-only",
        "ollama_url": url,
        "ollama_connected": ollama_ok,
        "ollama_error": err,
        "installed_models": models,
        "core_models_ready": {
            "qwen2.5:3b": any(m.startswith("qwen2.5:3b") for m in models),
            "llama3.2:3b": any(m.startswith("llama3.2:3b") for m in models),
        },
        "stats": {
            "total_prompts": len(prompt_files),
            "total_challenges": len(CHALLENGE_CATALOG),
            "total_findings": 9,
            "validation": {k: v for k, v in vstats.items() if k != "entries"},
        },
    }


@app.get("/api/benchmarks")
def api_benchmarks() -> Dict[str, Any]:
    if not BENCHMARKS_MD.exists():
        raise HTTPException(status_code=404, detail="lab/model-benchmarks.md not found")
    text = BENCHMARKS_MD.read_text(encoding="utf-8")
    summary = []
    tasks = []
    section = ""
    for line in text.splitlines():
        if line.startswith("## 1."):
            section = "summary"
            continue
        if line.startswith("## 2."):
            section = "tasks"
            continue
        if line.startswith("## 3."):
            section = ""
            continue
        if not line.startswith("|"):
            continue
        cols = [c.strip().strip("*`") for c in line.strip().strip("|").split("|")]
        if not cols or cols[0] in ("Model", "Task ID") or set(cols[0]) <= {"-"}:
            continue
        if section == "summary" and len(cols) >= 7:
            summary.append({
                "model": cols[0],
                "family": cols[1],
                "size": cols[2],
                "avg_prompt_tps": cols[3],
                "avg_gen_tps": cols[4],
                "avg_score": cols[5],
                "role": cols[6],
            })
        elif section == "tasks" and len(cols) >= 9:
            def _num(s: str) -> float:
                m = re.search(r"[\d.]+", s)
                return float(m.group(0)) if m else 0.0
            tasks.append({
                "task_id": cols[0],
                "task_name": cols[1],
                "llama_prompt_tps": _num(cols[2]),
                "llama_gen_tps": _num(cols[3]),
                "llama_score": _num(cols[4].split("/")[0]),
                "qwen_prompt_tps": _num(cols[5]),
                "qwen_gen_tps": _num(cols[6]),
                "qwen_score": _num(cols[7].split("/")[0]),
                "winner": cols[8],
            })
    return {"summary": summary, "tasks": tasks}


@app.get("/api/prompts")
def api_prompts() -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    all_items: List[Dict[str, Any]] = []
    for path in sorted(PROMPTS_DIR.rglob("*.md")):
        sec = parse_prompt_template(path)
        phase = sec.get("phase", path.parent.name).strip()
        tid = path.stem.split("-", 1)[0]
        vars_raw = sec.get("variables", "")
        variables = re.findall(r"\{\{([^}]+)\}\}", vars_raw or sec.get("template", ""))
        item = {
            "id": tid,
            "stem": path.stem,
            "title": sec.get("_title", path.stem),
            "phase": phase,
            "path": path.relative_to(ROOT).as_posix(),
            "variables": list(dict.fromkeys(v.strip() for v in variables)),
            "validation_hook": sec.get("validation hook", ""),
        }
        grouped.setdefault(phase, []).append(item)
        all_items.append(item)
    return {"total": len(all_items), "grouped": grouped, "items": all_items}


@app.get("/api/samples")
def api_samples() -> Dict[str, Any]:
    items = []
    for s in CHALLENGE_CATALOG + EXTRA_SAMPLES:
        p = ROOT / s["path"]
        items.append({**s, "exists": p.exists()})
    return {"samples": items}


@app.get("/api/challenges")
def api_challenges() -> Dict[str, Any]:
    eval_map: Dict[str, Any] = {}
    summary = {}
    if CHALLENGE_EVAL_JSON.exists():
        data = json.loads(CHALLENGE_EVAL_JSON.read_text(encoding="utf-8"))
        summary = data.get("summary", {})
        for r in data.get("results", []):
            eval_map[r["id"]] = r
    items = []
    for c in CHALLENGE_CATALOG:
        items.append({**c, "evaluation": eval_map.get(c["id"])})
    return {"summary": summary, "challenges": items}


async def _extract_analyze_payload(request: Request) -> Dict[str, Any]:
    ct = (request.headers.get("content-type") or "").lower()
    if "application/json" in ct:
        body = await request.json()
        return {
            "sample_id": body.get("sample_id"),
            "raw_text": body.get("raw_text") or "",
            "filename": body.get("filename") or "input.txt",
            "artifact_type": body.get("artifact_type") or "auto",
            "template_id": body.get("template_id") or "W1",
            "model": body.get("model") or "qwen2.5:3b",
            "extra_vars": body.get("extra_vars") or {},
        }
    form = await request.form()
    raw_text = str(form.get("raw_text") or "")
    filename = str(form.get("filename") or "input.txt")
    up = form.get("file")
    if up is not None and hasattr(up, "read") and getattr(up, "filename", None):
        raw_bytes = await up.read()
        raw_text = raw_bytes.decode("utf-8", errors="replace")
        filename = up.filename
    extra_vars = {}
    if form.get("extra_vars"):
        try:
            extra_vars = json.loads(str(form.get("extra_vars")))
        except json.JSONDecodeError:
            extra_vars = {}
    return {
        "sample_id": form.get("sample_id"),
        "raw_text": raw_text,
        "filename": filename,
        "artifact_type": str(form.get("artifact_type") or "auto"),
        "template_id": str(form.get("template_id") or "W1"),
        "model": str(form.get("model") or "qwen2.5:3b"),
        "extra_vars": extra_vars,
    }


def _resolve_input(payload: Dict[str, Any]) -> tuple[str, str, str]:
    raw_text = payload["raw_text"]
    filename = payload["filename"]
    atype = payload["artifact_type"]
    sample_id = payload.get("sample_id")
    if sample_id and not raw_text.strip():
        smap = _all_samples_map()
        if sample_id not in smap:
            raise HTTPException(status_code=404, detail=f"Sample not found: {sample_id}")
        sp = ROOT / smap[sample_id]["path"]
        if not sp.exists():
            raise HTTPException(status_code=404, detail=f"Sample file missing on disk: {sp}")
        raw_text = sp.read_text(encoding="utf-8", errors="replace")
        filename = sp.name
        if atype == "auto":
            atype = smap[sample_id]["artifact_type"]
    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Provide a file, sample_id, or raw_text.")
    return raw_text, filename, atype


@app.post("/api/analyze")
async def api_analyze(request: Request) -> Dict[str, Any]:
    payload = await _extract_analyze_payload(request)
    raw_text, filename, atype = _resolve_input(payload)
    ingested = _ingest_artifact(raw_text, filename, atype)
    tpl_path = find_template(payload["template_id"])
    sections = parse_prompt_template(tpl_path)
    variables = _build_template_vars(sections.get("template", ""), ingested, payload.get("extra_vars"))
    sys_p, usr_p = render_prompt(sections, variables)

    try:
        res = call_ollama(
            model=payload["model"],
            prompt=usr_p,
            system_prompt=sys_p,
            temperature=0.2,
            num_ctx=4096,
            num_predict=1024,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Local Ollama inference failed: {exc}") from exc

    return {
        "template_id": payload["template_id"],
        "template_title": sections.get("_title", tpl_path.stem),
        "filename": filename,
        "artifact_type": atype,
        "ingested_context": ingested,
        "model": res["model"],
        "output": res["response"],
        "telemetry": {k: v for k, v in res.items() if k != "response"},
    }


@app.post("/api/cross-check")
async def api_cross_check(request: Request) -> Dict[str, Any]:
    payload = await _extract_analyze_payload(request)
    raw_text, filename, atype = _resolve_input(payload)
    ingested = _ingest_artifact(raw_text, filename, atype)
    tpl_path = find_template(payload["template_id"])
    sections = parse_prompt_template(tpl_path)
    variables = _build_template_vars(sections.get("template", ""), ingested, payload.get("extra_vars"))
    sys_p, usr_p = render_prompt(sections, variables)

    results = {}
    for model in ("qwen2.5:3b", "llama3.2:3b"):
        try:
            res = call_ollama(
                model=model,
                prompt=usr_p,
                system_prompt=sys_p,
                temperature=0.2,
                num_ctx=4096,
                num_predict=1024,
            )
            results[model] = res
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Local Ollama cross-check failed on {model}: {exc}") from exc

    return {
        "template_id": payload["template_id"],
        "template_title": sections.get("_title", tpl_path.stem),
        "filename": filename,
        "ingested_context": ingested,
        "qwen": results["qwen2.5:3b"],
        "llama": results["llama3.2:3b"],
    }


class ValidationEntryReq(BaseModel):
    phase: str
    claim: str
    model: str
    source: str = "GUI Arena"
    check: str = "Human Analyst Review"
    result: str
    verdict: str  # Verified | Corrected | Hallucination


@app.get("/api/validation-log")
def api_get_validation_log() -> Dict[str, Any]:
    return _parse_validation_log()


@app.post("/api/validation-log")
def api_post_validation_log(entry: ValidationEntryReq) -> Dict[str, Any]:
    verdict_map = {
        "verified": "✅ Verified (L1/L3)",
        "corrected": "⚠️ Corrected (Partial)",
        "hallucination": "❌ Hallucination",
    }
    badge = verdict_map.get(entry.verdict.strip().lower(), entry.verdict)
    stats_before = _parse_validation_log()
    new_id = f"GUI-{stats_before['total'] + 1:03d}"

    def _clean(val: str) -> str:
        return " ".join(val.replace("|", "/").splitlines()).strip()[:180]

    row = (
        f"| {new_id} | {_clean(entry.phase)} | {_clean(entry.claim)} | {_clean(entry.model)} | "
        f"{_clean(entry.source)} | {_clean(entry.check)} | {_clean(entry.result)} | {badge} |\n"
    )
    VALIDATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not VALIDATION_LOG.exists():
        VALIDATION_LOG.write_text(
            "# Validation Log\n\n## Interactive GUI Validation Log\n\n| ID | Phase / Template | AI Claim / Output Summary | Model | Source Cited | Ground Truth Check | Result | Verdict |\n|---|---|---|---|---|---|---|---|\n",
            encoding="utf-8",
        )
    with VALIDATION_LOG.open("a", encoding="utf-8") as f:
        f.write(row)
    if EVIDENCE_LOG.exists():
        with EVIDENCE_LOG.open("a", encoding="utf-8") as f:
            f.write(row)

    updated = _parse_validation_log()
    return {"added_id": new_id, **updated}


@app.get("/api/ad-graph")
def api_ad_graph() -> Dict[str, Any]:
    if not BH_LAB_JSON.exists():
        raise HTTPException(status_code=404, detail="BloodHound lab JSON not found")
    data = load_bloodhound(BH_LAB_JSON)
    gt = compute_ground_truth(data)

    path_edge_ids = set()
    path_node_ids = set()
    for principal, edges in gt["paths_to_highvalue"].items():
        if edges:
            path_node_ids.add(principal)
            for e in edges:
                path_edge_ids.add(e["id"])
                path_node_ids.add(e["source"])
                path_node_ids.add(e["target"])

    return {
        "domain": data.get("domain", "LAB.LOCAL"),
        "nodes": data.get("nodes", []),
        "edges": data.get("edges", []),
        "ground_truth": gt,
        "highlighted_nodes": sorted(path_node_ids),
        "highlighted_edges": sorted(path_edge_ids),
    }


class CvssReq(BaseModel):
    vector: str


@app.post("/api/cvss")
def api_cvss(req: CvssReq) -> Dict[str, Any]:
    try:
        _, _, detail = score_vector(req.vector)
        return detail
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/report/diff")
def api_report_diff() -> Dict[str, Any]:
    ai_p = DELIVERABLES_DIR / "vapt-report-ai-draft.md"
    hu_p = DELIVERABLES_DIR / "vapt-report-human-edited.md"
    if not ai_p.exists() or not hu_p.exists():
        raise HTTPException(status_code=404, detail="Report markdown files not found")
    ai_text = ai_p.read_text(encoding="utf-8")
    hu_text = hu_p.read_text(encoding="utf-8")
    stats = analyze_diff(ai_text, hu_text)

    assets_dir = DELIVERABLES_DIR / "assets"
    pocs = []
    if assets_dir.exists():
        for img in sorted(assets_dir.glob("poc-*.png")):
            pocs.append({"name": img.name, "url": f"/deliverables/assets/{img.name}"})

    return {
        "stats": {k: v for k, v in stats.items() if k != "unified_diff"},
        "unified_diff_lines": stats["unified_diff"].splitlines()[:180],
        "ai_draft_preview": ai_text[:5000],
        "human_edited_preview": hu_text[:5000],
        "pocs": pocs,
    }


class ExportReq(BaseModel):
    target: str = "human_report"  # human_report | ai_draft | sop | presentation


@app.post("/api/report/export")
def api_report_export(req: ExportReq) -> Dict[str, Any]:
    target = req.target.lower()
    generated: List[Dict[str, Any]] = []

    if target == "human_report":
        pdf = DELIVERABLES_DIR / "VAPT-Report-Human-Edited.pdf"
        docx = DELIVERABLES_DIR / "VAPT-Report-Human-Edited.docx"
        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "reporting" / "build_vapt_report.py"),
            str(DELIVERABLES_DIR / "vapt-report-human-edited.md"),
            "--pdf", str(pdf),
            "--docx", str(docx),
            "--title", "VAPT Assessment Report — Human-Edited Final",
            "--subtitle", "Verified findings, calc_cvss.py scores, and live lab PoC evidence",
            "--doc-type", "Week 4 Deliverable — Human-Edited Final Report",
        ]
        subprocess.run(cmd, check=True)
        generated = [
            {"label": "Human-Edited Report (PDF)", "url": "/deliverables/VAPT-Report-Human-Edited.pdf", "bytes": pdf.stat().st_size},
            {"label": "Human-Edited Report (DOCX)", "url": "/deliverables/VAPT-Report-Human-Edited.docx", "bytes": docx.stat().st_size},
        ]
    elif target == "ai_draft":
        pdf = DELIVERABLES_DIR / "VAPT-Report-AI-Draft.pdf"
        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "reporting" / "build_vapt_report.py"),
            str(DELIVERABLES_DIR / "vapt-report-ai-draft.md"),
            "--pdf", str(pdf),
            "--title", "VAPT Assessment Report — Raw AI Draft",
            "--subtitle", "Unedited local LLM output prior to human QA and CVSS verification",
            "--doc-type", "Week 4 Deliverable — Raw AI Draft",
        ]
        subprocess.run(cmd, check=True)
        generated = [
            {"label": "Raw AI Draft Report (PDF)", "url": "/deliverables/VAPT-Report-AI-Draft.pdf", "bytes": pdf.stat().st_size},
        ]
    elif target == "sop":
        pdf = DELIVERABLES_DIR / "REUSABLE-VAPT-AI-SOP.pdf"
        docx = DELIVERABLES_DIR / "REUSABLE-VAPT-AI-SOP.docx"
        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "reporting" / "build_vapt_report.py"),
            str(DELIVERABLES_DIR / "REUSABLE-VAPT-AI-SOP.md"),
            "--pdf", str(pdf),
            "--docx", str(docx),
            "--title", "Reusable AI-Assisted VAPT Workflow SOP",
            "--subtitle", "Standard Operating Procedure for Privacy-First Local LLM Penetration Testing & QA",
            "--doc-type", "Standard Operating Procedure (SOP-VAPT-AI-01)",
        ]
        subprocess.run(cmd, check=True)
        generated = [
            {"label": "Reusable VAPT SOP (PDF)", "url": "/deliverables/REUSABLE-VAPT-AI-SOP.pdf", "bytes": pdf.stat().st_size},
            {"label": "Reusable VAPT SOP (DOCX)", "url": "/deliverables/REUSABLE-VAPT-AI-SOP.docx", "bytes": docx.stat().st_size},
        ]
    elif target == "presentation":
        pptx = DELIVERABLES_DIR / "DEPI-Project5-Presentation.pptx"
        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "reporting" / "build_presentation.py"),
            "--stats", str(ROOT / "evidence" / "week4" / "presentation-stats.json"),
            "--bench", str(ROOT / "evidence" / "week1" / "benchmark-raw.json"),
            "--out", str(pptx),
        ]
        subprocess.run(cmd, check=True)
        generated = [
            {"label": "DEPI Project 5 Defense Deck (PPTX)", "url": "/deliverables/DEPI-Project5-Presentation.pptx", "bytes": pptx.stat().st_size},
        ]
    else:
        raise HTTPException(status_code=400, detail=f"Unknown export target: {target}")

    return {"status": "ok", "target": target, "files": generated}
