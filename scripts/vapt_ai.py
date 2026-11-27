#!/usr/bin/env python3
"""Local-only Ollama runner for the AI-Assisted VAPT Automation Workflow.

Enforces Privacy Rule P1: refuses any non-local Ollama URL so test/lab data
never leaves the machine. Loads 7-field prompt templates from `prompts/`,
substitutes {{variables}}, executes inference on local models, and writes
structured markdown + raw telemetry JSON outputs.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "prompts"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}


def validate_local_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise SystemExit(
            f"[PRIVACY GATE P1 BLOCKED] Refusing non-local Ollama host: {url!r}. "
            "Only 127.0.0.1 / localhost is permitted."
        )
    return url.rstrip("/")


def parse_prompt_template(path: Path) -> Dict[str, str]:
    text = path.read_text(encoding="utf-8")
    sections: Dict[str, str] = {"_raw": text, "_title": path.stem}
    current_key: Optional[str] = None
    buf: List[str] = []

    for line in text.splitlines():
        if line.startswith("# ") and sections["_title"] == path.stem:
            sections["_title"] = line[2:].strip()
            continue
        if line.startswith("## "):
            if current_key is not None:
                sections[current_key] = "\n".join(buf).strip()
            current_key = line[3:].strip().lower()
            buf = []
        else:
            if current_key is not None:
                buf.append(line)
    if current_key is not None:
        sections[current_key] = "\n".join(buf).strip()
    return sections


def find_template(identifier: str) -> Path:
    """Resolve a prompt by ID/name only; callers cannot pass arbitrary file paths."""
    candidates = sorted(PROMPTS_DIR.rglob("*.md"))
    ident_low = Path(identifier.strip()).name.lower()
    for c in candidates:
        resolved = c.resolve()
        if not resolved.is_relative_to(PROMPTS_DIR.resolve()):
            continue
        if c.stem.lower() == ident_low or c.stem.lower().startswith(ident_low + "-"):
            return resolved
    raise FileNotFoundError(f"Prompt template not found for identifier: {identifier!r}")


def render_prompt(sections: Dict[str, str], variables: Dict[str, str]) -> tuple[str, str]:
    role = sections.get("role", "You are a penetration testing assistant.")
    anti_hall = sections.get("anti-hallucination rules", "")
    system_prompt = f"{role}\n\n{anti_hall}".strip()

    template_body = sections.get("template", "")
    if not template_body:
        raise ValueError("Template file has no '## Template' section.")

    def _replace(match: re.Match) -> str:
        key = match.group(1).strip()
        if key not in variables:
            raise ValueError(f"Missing required template variable: {{{{{key}}}}}")
        return variables[key]

    rendered = re.sub(r"\{\{([^}]+)\}\}", _replace, template_body)
    fmt = sections.get("expected output format", "")
    if fmt:
        rendered = f"{rendered}\n\nExpected output format:\n{fmt}"
    return system_prompt, rendered


def call_ollama(
    model: str,
    prompt: str,
    system_prompt: str = "",
    base_url: str = DEFAULT_OLLAMA_URL,
    temperature: float = 0.15,
    num_ctx: int = 6144,
    num_predict: int = 2048,
    timeout: int = 240,
) -> Dict:
    url = validate_local_url(base_url)
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
    }
    t0 = time.perf_counter()
    resp = requests.post(f"{url}/api/generate", json=payload, timeout=timeout)
    resp.raise_for_status()
    wall_s = time.perf_counter() - t0
    data = resp.json()

    prompt_eval_count = data.get("prompt_eval_count", 0) or 0
    prompt_eval_ns = data.get("prompt_eval_duration", 0) or 0
    eval_count = data.get("eval_count", 0) or 0
    eval_ns = data.get("eval_duration", 0) or 0
    load_ns = data.get("load_duration", 0) or 0
    total_ns = data.get("total_duration", 0) or 0

    return {
        "model": model,
        "response": (data.get("response") or "").strip(),
        "prompt_eval_count": prompt_eval_count,
        "prompt_eval_tok_s": round(prompt_eval_count / (prompt_eval_ns / 1e9), 2) if prompt_eval_ns else 0.0,
        "eval_count": eval_count,
        "eval_tok_s": round(eval_count / (eval_ns / 1e9), 2) if eval_ns else 0.0,
        "load_s": round(load_ns / 1e9, 2),
        "total_s": round(total_ns / 1e9, 2) if total_ns else round(wall_s, 2),
        "wall_s": round(wall_s, 2),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run grounded local VAPT prompts via Ollama.")
    ap.add_argument("--template", required=True, help="Template ID (e.g., R1, AD1, W2) or file path")
    ap.add_argument("--model", default="qwen2.5:3b", help="Local Ollama model name")
    ap.add_argument("--cross-check", action="store_true", help="Run both llama3.2:3b and qwen2.5:3b")
    ap.add_argument("--var", action="append", default=[], help="Variable key=value")
    ap.add_argument("--var-file", action="append", default=[], help="Variable key=filepath")
    ap.add_argument("--out", help="Output markdown file path")
    ap.add_argument("--json-out", help="Optional raw telemetry JSON output path")
    ap.add_argument("--url", default=DEFAULT_OLLAMA_URL, help="Local Ollama URL")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--num-ctx", type=int, default=4096)
    args = ap.parse_args()

    validate_local_url(args.url)
    tpl_path = find_template(args.template)
    sections = parse_prompt_template(tpl_path)

    variables: Dict[str, str] = {}
    for item in args.var:
        k, v = item.split("=", 1)
        variables[k.strip()] = v
    for item in args.var_file:
        k, fp = item.split("=", 1)
        variables[k.strip()] = Path(fp).read_text(encoding="utf-8")

    system_prompt, rendered_prompt = render_prompt(sections, variables)
    models = ["llama3.2:3b", "qwen2.5:3b"] if args.cross_check else [args.model]

    results = []
    for m in models:
        res = call_ollama(
            model=m,
            prompt=rendered_prompt,
            system_prompt=system_prompt,
            base_url=args.url,
            temperature=args.temperature,
            num_ctx=args.num_ctx,
        )
        results.append(res)

    md_parts = [
        f"# AI Run Output — {sections['_title']}",
        f"- **Template:** `{tpl_path.relative_to(ROOT).as_posix()}`",
        f"- **Models:** {', '.join(f'`{m}`' for m in models)}",
        "",
    ]
    for res in results:
        md_parts.extend([
            f"## Model: `{res['model']}`",
            f"- Prompt tokens: {res['prompt_eval_count']} ({res['prompt_eval_tok_s']} tok/s) | "
            f"Gen tokens: {res['eval_count']} ({res['eval_tok_s']} tok/s) | "
            f"Load: {res['load_s']}s | Total: {res['total_s']}s",
            "",
            res["response"],
            "",
        ])

    md_output = "\n".join(md_parts)
    if args.out:
        out_p = Path(args.out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(md_output, encoding="utf-8")
        print(f"OK wrote {out_p}")
    else:
        print(md_output)

    if args.json_out:
        jp = Path(args.json_out)
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(
            json.dumps(
                {
                    "template": str(tpl_path.relative_to(ROOT)),
                    "system_prompt": system_prompt,
                    "prompt": rendered_prompt,
                    "results": results,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"OK wrote {jp}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
