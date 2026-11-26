/* Localhost-only Dark GUI controller for DEPI Project 5 */
const state = {
  samples: [],
  prompts: [],
  challenges: [],
  lastCrossCheck: null,
  cy: null,
  charts: {},
};

function escHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderMarkdown(md) {
  let text = escHtml(md || "");
  text = text.replace(/```([\w-]*)\n([\s\S]*?)```/g, (_, lang, code) => `<pre><code>${code}</code></pre>`);
  text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
  text = text.replace(/^### (.*)$/gm, "<h3>$1</h3>");
  text = text.replace(/^## (.*)$/gm, "<h2>$1</h2>");
  text = text.replace(/^# (.*)$/gm, "<h1>$1</h1>");
  text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/^\s*[-*]\s+(.*)$/gm, "<li>$1</li>");
  text = text.replace(/\n{2,}/g, "<br><br>");
  text = text.replace(/\n/g, "<br>");
  return text;
}

async function apiJson(url, opts = {}) {
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

/* ---------- Tabs ---------- */
function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === tabId));
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === tabId));
  if (tabId === "tab-graph" && state.cy) {
    setTimeout(() => { state.cy.resize(); state.cy.fit(undefined, 30); }, 60);
  }
}

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

/* ---------- Health & KPIs ---------- */
async function loadHealth() {
  try {
    const h = await apiJson("/api/health");
    const ob = document.getElementById("ollama-badge");
    ob.textContent = h.ollama_connected ? "Ollama Online (11434)" : "Ollama Offline";
    ob.className = `badge ${h.ollama_connected ? "ok" : "err"}`;

    const mb = document.getElementById("models-badge");
    const ready = Object.entries(h.core_models_ready).filter(([, v]) => v).map(([k]) => k);
    mb.textContent = ready.length ? `Models: ${ready.join(", ")}` : "Models missing";
    mb.className = `badge ${ready.length === 2 ? "ok" : "warn"}`;

    const v = h.stats.validation;
    document.getElementById("kpi-prompts").textContent = h.stats.total_prompts;
    document.getElementById("kpi-challenges").textContent = h.stats.total_challenges;
    document.getElementById("kpi-accuracy").textContent = `${v.accuracy_pct}%`;
    document.getElementById("kpi-usable").textContent = `Usable after QA: ${v.usable_pct}%`;
    document.getElementById("kpi-hallucination").textContent = `${v.hallucination_pct}%`;
    document.getElementById("kpi-total-claims").textContent = `Logged claims: ${v.total} (${v.verified}✅ / ${v.corrected}⚠️ / ${v.hallucinated}❌)`;
  } catch (e) {
    document.getElementById("ollama-badge").textContent = "Health Error";
  }
}

/* ---------- Benchmarks (Chart.js) ---------- */
async function loadBenchmarks() {
  const b = await apiJson("/api/benchmarks");
  const labels = b.tasks.map((t) => `${t.task_id}: ${t.task_name.split(" ").slice(0, 2).join(" ")}`);
  const qwenTps = b.tasks.map((t) => t.qwen_gen_tps);
  const llamaTps = b.tasks.map((t) => t.llama_gen_tps);
  const qwenScore = b.tasks.map((t) => t.qwen_score);
  const llamaScore = b.tasks.map((t) => t.llama_score);

  if (typeof Chart === "undefined") return;
  const commonOpts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: "#cbd5e1" } } },
    scales: {
      x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.1)" } },
      y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.1)" }, beginAtZero: true },
    },
  };

  if (state.charts.tps) state.charts.tps.destroy();
  state.charts.tps = new Chart(document.getElementById("chart-tps"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        { label: "qwen2.5:3b (tok/s)", data: qwenTps, backgroundColor: "rgba(20,184,166,0.8)" },
        { label: "llama3.2:3b (tok/s)", data: llamaTps, backgroundColor: "rgba(56,189,248,0.75)" },
      ],
    },
    options: commonOpts,
  });

  if (state.charts.score) state.charts.score.destroy();
  state.charts.score = new Chart(document.getElementById("chart-score"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        { label: "qwen2.5:3b (score /5)", data: qwenScore, backgroundColor: "rgba(16,185,129,0.8)" },
        { label: "llama3.2:3b (score /5)", data: llamaScore, backgroundColor: "rgba(245,158,11,0.75)" },
      ],
    },
    options: { ...commonOpts, scales: { ...commonOpts.scales, y: { ...commonOpts.scales.y, max: 5 } } },
  });
}

/* ---------- Prompts, Samples, Challenges ---------- */
async function loadPromptsAndSamples() {
  const [pData, sData, cData] = await Promise.all([
    apiJson("/api/prompts"),
    apiJson("/api/samples"),
    apiJson("/api/challenges"),
  ]);
  state.prompts = pData.items;
  state.samples = sData.samples;
  state.challenges = cData.challenges;

  for (const selId of ["an-template", "ar-template"]) {
    const sel = document.getElementById(selId);
    sel.innerHTML = "";
    for (const [phase, list] of Object.entries(pData.grouped)) {
      const og = document.createElement("optgroup");
      og.label = phase.toUpperCase();
      for (const item of list) {
        const opt = document.createElement("option");
        opt.value = item.id;
        opt.textContent = `${item.id} — ${item.title.replace(/^[^—]+—\s*/, "")}`;
        if (item.id === "W1") opt.selected = true;
        og.appendChild(opt);
      }
      sel.appendChild(og);
    }
  }

  for (const selId of ["an-sample", "ar-sample"]) {
    const sel = document.getElementById(selId);
    sel.innerHTML = '<option value="">-- Select Challenge or Lab Sample --</option>';
    for (const s of sData.samples) {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = `[${s.suite}] ${s.name}`;
      sel.appendChild(opt);
    }
  }

  const tbody = document.getElementById("challenges-tbody");
  tbody.innerHTML = "";
  if (cData.summary && cData.summary.total) {
    document.getElementById("kpi-challenge-eval").textContent =
      `Passive Accuracy: ${cData.summary.passed}/${cData.summary.total} (${cData.summary.pass_rate_pct}%)`;
    document.getElementById("challenge-eval-summary").textContent =
      `Evaluated ${cData.summary.total} challenges locally: ${cData.summary.passed}/${cData.summary.total} passed`;
  }
  for (const ch of cData.challenges) {
    const ev = ch.evaluation;
    const evHtml = ev
      ? `<span class="badge ${ev.passed ? "ok" : "warn"}">${ev.passed ? "✅ Diagnosed" : "⚠️ Partial"} (${ev.gen_tps} t/s)</span>`
      : `<span class="badge">Ready for Passive Run</span>`;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${escHtml(ch.suite)}</strong></td>
      <td>${escHtml(ch.name)}</td>
      <td><code>${escHtml(ch.target_param)}</code></td>
      <td>${escHtml(ch.expected_vuln)}</td>
      <td>${evHtml}</td>
      <td class="btn-row">
        <button class="btn sm primary" data-load-an="${escHtml(ch.id)}">Analyze</button>
        <button class="btn sm" data-load-ar="${escHtml(ch.id)}">Arena</button>
      </td>
    `;
    tbody.appendChild(tr);
  }

  tbody.querySelectorAll("[data-load-an]").forEach((b) => {
    b.addEventListener("click", () => {
      document.getElementById("an-sample").value = b.dataset.loadAn;
      document.getElementById("an-template").value = "W1";
      document.getElementById("an-atype").value = "http";
      switchTab("tab-analyzer");
    });
  });
  tbody.querySelectorAll("[data-load-ar]").forEach((b) => {
    b.addEventListener("click", () => {
      document.getElementById("ar-sample").value = b.dataset.loadAr;
      document.getElementById("ar-template").value = "W1";
      document.getElementById("ar-atype").value = "http";
      switchTab("tab-arena");
    });
  });

  document.getElementById("an-sample").addEventListener("change", (e) => {
    const found = state.samples.find((s) => s.id === e.target.value);
    if (found) {
      document.getElementById("an-template").value = found.recommended_template;
      document.getElementById("an-atype").value = found.artifact_type;
    }
  });
  document.getElementById("ar-sample").addEventListener("change", (e) => {
    const found = state.samples.find((s) => s.id === e.target.value);
    if (found) {
      document.getElementById("ar-template").value = found.recommended_template;
      document.getElementById("ar-atype").value = found.artifact_type;
    }
  });
}

/* ---------- Tab 2: Analyzer ---------- */
document.getElementById("an-run-btn").addEventListener("click", async () => {
  const btn = document.getElementById("an-run-btn");
  const status = document.getElementById("an-status");
  btn.disabled = true;
  status.textContent = "Running local Ollama inference...";
  try {
    const fd = new FormData();
    const fileInput = document.getElementById("an-file");
    if (fileInput.files && fileInput.files[0]) {
      fd.append("file", fileInput.files[0]);
    } else {
      fd.append("sample_id", document.getElementById("an-sample").value);
    }
    fd.append("raw_text", document.getElementById("an-raw").value);
    fd.append("artifact_type", document.getElementById("an-atype").value);
    fd.append("template_id", document.getElementById("an-template").value);
    fd.append("model", document.getElementById("an-model").value);

    const data = await apiJson("/api/analyze", { method: "POST", body: fd });
    document.getElementById("an-ingested").textContent = data.ingested_context;
    document.getElementById("an-output").innerHTML = renderMarkdown(data.output);
    const t = data.telemetry;
    document.getElementById("an-telemetry").textContent =
      `${data.model} | ${t.eval_count} tok @ ${t.eval_tok_s} tok/s | ${t.total_s}s`;
    status.textContent = `Completed on ${data.filename}`;
  } catch (e) {
    status.textContent = `Error: ${e.message}`;
  } finally {
    btn.disabled = false;
  }
});

/* ---------- Tab 3: Cross-Model Arena & Validation Log ---------- */
document.getElementById("ar-run-btn").addEventListener("click", async () => {
  const btn = document.getElementById("ar-run-btn");
  const status = document.getElementById("ar-status");
  btn.disabled = true;
  status.textContent = "Running Qwen 2.5 then Llama 3.2 sequentially...";
  try {
    const data = await apiJson("/api/cross-check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sample_id: document.getElementById("ar-sample").value,
        artifact_type: document.getElementById("ar-atype").value,
        template_id: document.getElementById("ar-template").value,
      }),
    });
    state.lastCrossCheck = data;
    document.getElementById("ar-qwen-out").innerHTML = renderMarkdown(data.qwen.response);
    document.getElementById("ar-llama-out").innerHTML = renderMarkdown(data.llama.response);
    document.getElementById("ar-qwen-tel").textContent = `${data.qwen.eval_tok_s} tok/s | ${data.qwen.total_s}s`;
    document.getElementById("ar-llama-tel").textContent = `${data.llama.eval_tok_s} tok/s | ${data.llama.total_s}s`;
    document.getElementById("val-claim").value = `${data.template_id} on ${data.filename}`;
    status.textContent = "Cross-check complete. Review side-by-side and log verdict below.";
  } catch (e) {
    status.textContent = `Error: ${e.message}`;
  } finally {
    btn.disabled = false;
  }
});

async function loadValidationLog() {
  const v = await apiJson("/api/validation-log");
  document.getElementById("val-count").textContent = v.total;
  const tbody = document.getElementById("val-tbody");
  tbody.innerHTML = "";
  for (const r of [...v.entries].reverse()) {
    const tr = document.createElement("tr");
    const cls = r.status === "Verified" ? "ok" : r.status === "Hallucination" ? "err" : "warn";
    tr.innerHTML = `
      <td><code>${escHtml(r.id)}</code></td>
      <td>${escHtml(r.phase)}</td>
      <td>${escHtml(r.claim)}</td>
      <td><code>${escHtml(r.model)}</code></td>
      <td>${escHtml(r.result)}</td>
      <td><span class="badge ${cls}">${escHtml(r.verdict)}</span></td>
    `;
    tbody.appendChild(tr);
  }
}

document.querySelectorAll("[data-verdict]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const verdict = btn.dataset.verdict;
    const claim = document.getElementById("val-claim").value.trim() || "GUI Arena cross-model evaluation";
    const result = document.getElementById("val-note").value.trim() || `Marked ${verdict} by human reviewer`;
    const model = document.getElementById("val-model").value;
    const tpl = document.getElementById("ar-template").value || "GUI";
    const status = document.getElementById("val-status");
    try {
      const res = await apiJson("/api/validation-log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phase: `GUI ${tpl}`, claim, model, source: "Arena", check: "Human Review", result, verdict }),
      });
      status.textContent = `Logged ${res.added_id} (${verdict}). Updated Accuracy: ${res.accuracy_pct}%`;
      await Promise.all([loadValidationLog(), loadHealth()]);
    } catch (e) {
      status.textContent = `Error: ${e.message}`;
    }
  });
});

/* ---------- Tab 4: AD Graph (Cytoscape.js) ---------- */
async function loadAdGraph() {
  const g = await apiJson("/api/ad-graph");
  const hlNodes = new Set(g.highlighted_nodes);
  const hlEdges = new Set(g.highlighted_edges);

  const elements = [];
  for (const n of g.nodes) {
    elements.push({
      data: {
        id: n.id,
        label: n.id.replace("@LAB.LOCAL", ""),
        type: n.type,
        highvalue: !!n.highvalue,
        kerberoastable: !!n.kerberoastable,
        asrep_roastable: !!n.asrep_roastable,
        spn: n.spn || "",
        description: n.description || "",
        in_path: hlNodes.has(n.id),
      },
    });
  }
  for (const e of g.edges) {
    elements.push({
      data: {
        id: e.id,
        source: e.source,
        target: e.target,
        label: `${e.id}: ${e.right}`,
        right: e.right,
        is_acl: !!e.is_acl,
        in_path: hlEdges.has(e.id),
      },
    });
  }

  const pathsDiv = document.getElementById("graph-paths-list");
  pathsDiv.innerHTML = Object.entries(g.ground_truth.paths_to_highvalue)
    .filter(([, p]) => p && p.length)
    .map(([u, edges]) => `<div><strong>${escHtml(u.replace("@LAB.LOCAL",""))}</strong>: ${edges.map((e) => `${escHtml(e.id)}(${escHtml(e.right)})`).join(" &rarr; ")}</div>`)
    .join("");

  if (typeof cytoscape === "undefined") return;
  const presetPositions = {
    "m.ali@LAB.LOCAL": { x: 110, y: 80 },
    "svc-backup@LAB.LOCAL": { x: 110, y: 220 },
    "IT-ADMINS@LAB.LOCAL": { x: 110, y: 360 },
    "DOMAIN ADMINS@LAB.LOCAL": { x: 280, y: 490 },
    "j.smith@LAB.LOCAL": { x: 430, y: 80 },
    "svc-sync@LAB.LOCAL": { x: 430, y: 240 },
    "LAB.LOCAL": { x: 430, y: 400 },
    "helpdesk01@LAB.LOCAL": { x: 740, y: 80 },
    "HELP-DESK@LAB.LOCAL": { x: 740, y: 240 },
    "s.nabil@LAB.LOCAL": { x: 740, y: 400 },
    "DC01.LAB.LOCAL": { x: 280, y: 80 },
  };
  state.cy = cytoscape({
    container: document.getElementById("cy"),
    elements,
    layout: { name: "preset", positions: (node) => presetPositions[node.id()] || { x: 300, y: 250 }, padding: 42 },
    style: [
      {
        selector: "node",
        style: {
          label: "data(label)",
          "background-color": (ele) => ele.data("highvalue") ? "#f43f5e" : ele.data("type") === "Group" ? "#38bdf8" : "#14b8a6",
          color: "#f8fafc",
          "font-size": "11px",
          "font-weight": 600,
          "text-valign": "bottom",
          "text-margin-y": 7,
          "text-background-color": "#080e1c",
          "text-background-opacity": 0.85,
          "text-background-padding": 2,
          width: 32,
          height: 32,
          "border-width": (ele) => ele.data("in_path") ? 3 : 1,
          "border-color": (ele) => ele.data("in_path") ? "#f59e0b" : "#334155",
        },
      },
      {
        selector: "edge",
        style: {
          label: "data(label)",
          "curve-style": "bezier",
          "control-point-step-size": 45,
          "target-arrow-shape": "triangle",
          "line-color": (ele) => ele.data("in_path") ? "#f59e0b" : "#475569",
          "target-arrow-color": (ele) => ele.data("in_path") ? "#f59e0b" : "#475569",
          width: (ele) => ele.data("in_path") ? 3 : 1.5,
          color: "#cbd5e1",
          "font-size": "9.5px",
          "text-rotation": "autorotate",
          "text-background-color": "#080e1c",
          "text-background-opacity": 0.9,
          "text-background-padding": 2,
        },
      },
    ],
  });

  state.cy.on("tap", "node", (evt) => {
    const d = evt.target.data();
    document.getElementById("graph-inspector").innerHTML = `
      <div><strong>Principal:</strong> <code>${escHtml(d.id)}</code></div>
      <div><strong>Type:</strong> ${escHtml(d.type)} | <strong>High Value:</strong> ${d.highvalue}</div>
      <div><strong>Kerberoastable:</strong> ${d.kerberoastable} ${d.spn ? `(<code>${escHtml(d.spn)}</code>)` : ""}</div>
      <div><strong>AS-REP Roastable:</strong> ${d.asrep_roastable}</div>
      <div><strong>Description:</strong> ${escHtml(d.description || "—")}</div>
    `;
  });
  state.cy.on("tap", "edge", (evt) => {
    const d = evt.target.data();
    document.getElementById("graph-inspector").innerHTML = `
      <div><strong>Edge:</strong> <code>${escHtml(d.id)}</code> (${escHtml(d.right)})</div>
      <div><strong>Source:</strong> <code>${escHtml(d.source)}</code></div>
      <div><strong>Target:</strong> <code>${escHtml(d.target)}</code></div>
      <div><strong>ACL Abuse:</strong> ${d.is_acl} | <strong>On Shortest Path:</strong> ${d.in_path}</div>
    `;
  });

  document.getElementById("graph-fit").addEventListener("click", () => state.cy.fit(undefined, 30));
  document.getElementById("graph-all-paths").addEventListener("click", () => state.cy.fit(undefined, 30));
}

/* ---------- Tab 5: CVSS, Diff, PoCs & Export ---------- */
function syncVectorFromSelectors() {
  const v = [
    "CVSS:3.1",
    `AV:${document.getElementById("cvss-av").value}`,
    `AC:${document.getElementById("cvss-ac").value}`,
    `PR:${document.getElementById("cvss-pr").value}`,
    `UI:${document.getElementById("cvss-ui").value}`,
    `S:${document.getElementById("cvss-s").value}`,
    `C:${document.getElementById("cvss-c").value}`,
    `I:${document.getElementById("cvss-i").value}`,
    `A:${document.getElementById("cvss-a").value}`,
  ].join("/");
  document.getElementById("cvss-vector").value = v;
  computeCvss();
}

async function computeCvss() {
  const vec = document.getElementById("cvss-vector").value.trim();
  const badge = document.getElementById("cvss-result");
  try {
    const d = await apiJson("/api/cvss", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ vector: vec }),
    });
    const cls = d.base_score >= 9 ? "err" : d.base_score >= 7 ? "warn" : "ok";
    badge.className = `badge ${cls}`;
    badge.textContent = `${d.base_score.toFixed(1)} ${d.severity} (ISS=${d.iss}, Exploitability=${d.exploitability})`;
  } catch (e) {
    badge.className = "badge err";
    badge.textContent = `Invalid Vector: ${e.message}`;
  }
}

document.querySelectorAll(".cvss-sel").forEach((s) => s.addEventListener("change", syncVectorFromSelectors));
document.getElementById("cvss-calc-btn").addEventListener("click", computeCvss);

async function loadDiffAndGallery() {
  const d = await apiJson("/api/report/diff");
  const st = d.stats;
  document.getElementById("diff-stats").textContent =
    `AI Draft: ${st.ai_words} words -> Human Final: ${st.human_words} words | Similarity: ${st.word_similarity_pct}% | Deleted: ${st.removed_words} words`;

  document.getElementById("diff-box").innerHTML = d.unified_diff_lines
    .map((line) => {
      const esc = escHtml(line);
      if (line.startsWith("+") && !line.startsWith("+++")) return `<span class="diff-add">${esc}</span>`;
      if (line.startsWith("-") && !line.startsWith("---")) return `<span class="diff-del">${esc}</span>`;
      if (line.startsWith("@@")) return `<span class="diff-hdr">${esc}</span>`;
      return `<span>${esc}</span><br>`;
    })
    .join("");

  const gal = document.getElementById("poc-gallery");
  gal.innerHTML = d.pocs
    .map((p) => `<div class="poc-card" data-img="${escHtml(p.url)}"><img src="${escHtml(p.url)}" alt="${escHtml(p.name)}" /><div class="cap">${escHtml(p.name)}</div></div>`)
    .join("");

  const modal = document.getElementById("img-modal");
  gal.querySelectorAll(".poc-card").forEach((c) => {
    c.addEventListener("click", () => {
      document.getElementById("img-modal-src").src = c.dataset.img;
      modal.classList.add("open");
    });
  });
  modal.addEventListener("click", () => modal.classList.remove("open"));
}

document.querySelectorAll("[data-export]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const target = btn.dataset.export;
    const status = document.getElementById("export-status");
    btn.disabled = true;
    status.textContent = `Building ${target}...`;
    try {
      const res = await apiJson("/api/report/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target }),
      });
      status.innerHTML = res.files
        .map((f) => `<a href="${escHtml(f.url)}" target="_blank" style="color:var(--teal);font-weight:700;">Download ${escHtml(f.label)} (${Math.round(f.bytes / 1024)} KB)</a>`)
        .join(" &middot; ");
    } catch (e) {
      status.textContent = `Export failed: ${e.message}`;
    } finally {
      btn.disabled = false;
    }
  });
});

/* ---------- Boot ---------- */
(async function init() {
  await Promise.all([
    loadHealth(),
    loadBenchmarks(),
    loadPromptsAndSamples(),
    loadValidationLog(),
    loadAdGraph(),
    loadDiffAndGallery(),
    computeCvss(),
  ]);
})();
