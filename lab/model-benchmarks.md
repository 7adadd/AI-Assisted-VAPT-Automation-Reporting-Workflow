# Local Model Benchmarks (Week 1 Deliverable)

**Machine:** AMD Ryzen 5 5600H · 16 GB RAM · NVIDIA RTX 3050 Ti Laptop (4 GB VRAM, CUDA active)  
**Runtime:** Ollama v0.40.2 (Windows native, `http://127.0.0.1:11434`, 100% local)  
**Benchmark Script:** `scripts/run_benchmarks.py` · **Raw Telemetry:** `evidence/week1/benchmark-raw.json`  
**Measured:** 2026-11-26

---

## 1. Model Inventory Summary

| Model | Family | Size on Disk | Avg Prompt tok/s | Avg Gen tok/s | Avg Grounding Score | Role in Workflow |
|---|---|---|---|---|---|---|
| **`qwen2.5:3b`** | Qwen 2.5 | 1.9 GB | 1064.4 | **69.3** | **5.0 / 5.0** | **Primary** (AD, Code, Scripts, Reporting) |
| **`llama3.2:3b`** | Llama 3.2 | 2.0 GB | **1313.3** | 39.3 | 4.3 / 5.0 | **Secondary / Cross-Check** (Fast triage + L3 comparison) |
| `llama-guard3:1b` | Llama Guard | 1.6 GB | — | — | — | Out of scope (primary AI red-teaming project) |
| `sentinel-*` | Custom 3B | 2.0 GB ea | — | — | — | Out of scope (primary AI red-teaming project — untouched) |

---

## 2. Per-Task Benchmark Matrix (6 Fixed Tasks × 2 Local Models)

| Task ID | Task Name | `llama3.2:3b` Prompt tok/s | `llama3.2:3b` Gen tok/s | `llama3.2:3b` Score | `qwen2.5:3b` Prompt tok/s | `qwen2.5:3b` Gen tok/s | `qwen2.5:3b` Score | Winner |
|---|---|---|---|---|---|---|---|---|
| **T1** | Nmap Scan Triage | 1605.3 | 39.2 | 5/5 (4/4) | 1379.3 | **65.4** | **5/5 (4/4)** | `qwen2.5:3b` (faster gen) |
| **T2** | BloodHound Edge Explanation | 1446.2 | 41.7 | 4/5 (2/3) | 1103.5 | **69.8** | **5/5 (3/3)** | `qwen2.5:3b` (full citations) |
| **T3** | XSS Payload Suggestion (Constrained) | 1086.5 | 39.7 | 5/5 (1/1) | 1066.9 | **71.7** | **5/5 (1/1)** | `qwen2.5:3b` (1.8× faster) |
| **T4** | Finding Paragraph Rewrite | 1342.2 | 36.8 | 3/5 (1/2) | 826.0 | **66.4** | **5/5 (2/2)** | `qwen2.5:3b` (strict grounding) |
| **T5** | PowerShell SPN Audit Script | 1107.0 | 41.0 | 5/5 (2/2) | 651.6 | **71.3** | **5/5 (2/2)** | `qwen2.5:3b` (clean cmdlet syntax) |
| **T6** | Decompiled Java Review | 1292.4 | 37.4 | 4/5 (2/3) | 1359.2 | **71.5** | **5/5 (3/3)** | `qwen2.5:3b` (exact line citations) |

---

## 3. Key Takeaways & Phase Routing Decision

1. **VRAM Fit Matters:** Both 3B Q4 models fit completely inside the RTX 3050 Ti's 4 GB VRAM, achieving **39–72 tok/s** generation without CPU offloading bottlenecks.
2. **Why `qwen2.5:3b` Won Primary Status:** `qwen2.5:3b` scored **5/5 on all 6 benchmark tasks** and generated output **76% faster** on average (`69.3` vs `39.3 tok/s`), with noticeably tighter adherence to `<DATA>` citations (especially on T2 BloodHound edges, T4 SQLi finding rewrite, and T6 Java line references).
3. **Why We Still Keep `llama3.2:3b`:** Used as our **independent L3 Cross-Model Verification engine** (`scripts/vapt_ai.py --cross-check`). Comparing two different model families exposed real failure modes (e.g., `llama3.2:3b` swapping SPN/AS-REP accounts in AD5 or misclassifying read-only SQLi/LFI payloads as destructive in W5), proving why human validation gates are essential.
4. **Reproduce:**
   ```bash
   python scripts/run_benchmarks.py
   ```
