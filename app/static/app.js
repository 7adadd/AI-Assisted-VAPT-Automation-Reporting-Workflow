/* ============================================================
   VAPT Studio — localhost-only controller
   Talks exclusively to the FastAPI backend on 127.0.0.1:8000
   ============================================================ */
const state = {
  samples: [],
  challenges: [],
  srcMode: 'paste',
  template: 'W1',
  uploadedFile: null,
  lastRun: null,
  cy: null,
  charts: {},
};

const $  = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

/* ---------- tiny markdown renderer (no external deps) ---------- */
function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function mdInline(s) {
  return esc(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|\s)\*([^*\n]+)\*/g, '$1<em>$2</em>');
}
function renderMarkdown(src) {
  const lines = String(src || '').split('\n');
  let html = '', inCode = false, codeBuf = [], inList = false, inQuote = false;

  const closeList = () => { if (inList) { html += '</ul>'; inList = false; } };
  const closeQuote = () => { if (inQuote) { html += '</blockquote>'; inQuote = false; } };

  for (const raw of lines) {
    const line = raw.replace(/\s+$/, '');

    if (/^```/.test(line)) {
      if (inCode) { html += `<pre><code>${esc(codeBuf.join('\n'))}</code></pre>`; codeBuf = []; inCode = false; }
      else { closeList(); closeQuote(); inCode = true; }
      continue;
    }
    if (inCode) { codeBuf.push(raw); continue; }

    if (/^\s*$/.test(line)) { closeList(); closeQuote(); continue; }

    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      closeList(); closeQuote();
      const lvl = Math.min(h[1].length + 1, 4);
      html += `<h${lvl}>${mdInline(h[2])}</h${lvl}>`;
      continue;
    }
    if (/^>\s?/.test(line)) {
      closeList();
      if (!inQuote) { html += '<blockquote>'; inQuote = true; }
      html += mdInline(line.replace(/^>\s?/, '')) + '<br/>';
      continue;
    }
    closeQuote();
    const li = line.match(/^\s*[-*+]\s+(.*)$/);
    if (li) {
      if (!inList) { html += '<ul>'; inList = true; }
      html += `<li>${mdInline(li[1])}</li>`;
      continue;
    }
    closeList();
    if (/^\s*\|/.test(line)) continue;           // tables are rare in model output
    html += `<p>${mdInline(line)}</p>`;
  }
  if (inCode && codeBuf.length) html += `<pre><code>${esc(codeBuf.join('\n'))}</code></pre>`;
  closeList(); closeQuote();
  return html;
}

async function api(path, opts = {}) {
  const method = (opts.method || 'GET').toUpperCase();
  const headers = new Headers(opts.headers || {});
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const session = document.querySelector('meta[name="vapt-session"]')?.content;
    if (session) headers.set('X-VAPT-Session', session);
  }
  const res = await fetch(path, { ...opts, headers });
  const txt = await res.text();
  let data; try { data = txt ? JSON.parse(txt) : {}; } catch { data = { raw: txt }; }
  if (!res.ok) throw new Error(data.detail || data.raw || `HTTP ${res.status}`);
  return data;
}

/* ---------- navigation ---------- */
$$('.nav-btn').forEach(btn => btn.addEventListener('click', () => {
  $$('.nav-btn').forEach(b => { b.classList.remove('active'); b.removeAttribute('aria-current'); });
  $$('.view').forEach(v => v.classList.remove('active'));
  btn.classList.add('active');
  btn.setAttribute('aria-current', 'page');
  $('#view-' + btn.dataset.view).classList.add('active');
  if (btn.dataset.view === 'dashboard') loadDashboard();
  if (btn.dataset.view === 'graph') loadGraph();
  if (btn.dataset.view === 'reports') loadReports();
}));

/* ---------- step 1: source mode ---------- */
$$('#src-seg button').forEach(b => b.addEventListener('click', () => {
  $$('#src-seg button').forEach(x => { x.classList.remove('on'); x.setAttribute('aria-pressed', 'false'); });
  b.classList.add('on');
  b.setAttribute('aria-pressed', 'true');
  state.srcMode = b.dataset.src;
  $('#src-paste').style.display   = state.srcMode === 'paste'  ? '' : 'none';
  $('#src-upload').style.display  = state.srcMode === 'upload' ? '' : 'none';
  $('#src-url').style.display     = state.srcMode === 'url'    ? '' : 'none';
}));

const dropZone = $('#drop-zone');
dropZone.addEventListener('keydown', ev => {
  if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); $('#in-file').click(); }
});
['dragenter', 'dragover'].forEach(e => dropZone.addEventListener(e, ev => {
  ev.preventDefault(); dropZone.classList.add('over');
}));
['dragleave', 'drop'].forEach(e => dropZone.addEventListener(e, ev => {
  ev.preventDefault(); dropZone.classList.remove('over');
}));
dropZone.addEventListener('drop', ev => {
  const f = ev.dataTransfer.files[0];
  if (f) { state.uploadedFile = f; dropZone.innerHTML = `<b>${esc(f.name)}</b><br/><span class="muted">${(f.size/1024).toFixed(1)} KB</span>`; }
});
$('#in-file').addEventListener('change', ev => {
  const f = ev.target.files[0];
  if (f) { state.uploadedFile = f; dropZone.innerHTML = `<b>${esc(f.name)}</b><br/><span class="muted">${(f.size/1024).toFixed(1)} KB</span>`; }
});

/* ---------- step 2: review type ---------- */
$$('#review-grid .review-card').forEach(c => c.addEventListener('click', () => {
  $$('#review-grid .review-card').forEach(x => { x.classList.remove('on'); x.setAttribute('aria-pressed', 'false'); });
  c.classList.add('on');
  c.setAttribute('aria-pressed', 'true');
  state.template = c.dataset.tpl;
}));

/* ---------- inspect a real PortSwigger lab instance (passive GET) ---------- */
$('#btn-import').addEventListener('click', async () => {
  const url = $('#in-url').value.trim();
  if (!url) return;
  const btn = $('#btn-import');
  const old = btn.innerHTML;
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Inspecting…';
  try {
    const r = await api('/api/lab/inspect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    // Real observed attack surface — not a description the model could guess from.
    $('#in-text').value = r.context;
    $('#result-hint').textContent = '';
    dropZone.innerHTML = `<b>${esc(r.origin)}</b><br/><span class="muted">${r.pages_fetched} pages &middot; ${r.query_params.length} params &middot; ${r.form_count} forms</span>`;
    state.uploadedFile = null;
    $$('#src-seg button').forEach(x => x.classList.toggle('on', x.dataset.src === 'paste'));
    $('#src-paste').style.display = ''; $('#src-upload').style.display = 'none'; $('#src-url').style.display = 'none';
    state.srcMode = 'paste';
    $$('#review-grid .review-card').forEach(x => x.classList.toggle('on', x.dataset.tpl === 'PS1'));
    state.template = 'PS1';
    $('#result-card').classList.remove('show');
  } catch (e) {
    alert('Inspection failed: ' + e.message);
  } finally {
    btn.disabled = false; btn.innerHTML = old;
  }
});

/* ---------- run ---------- */
async function runAnalysis(cross) {
  const btn = cross ? $('#btn-cross') : $('#btn-run');
  const old = btn.innerHTML;
  const hasUpload = state.srcMode === 'upload' && !!state.uploadedFile;
  const hasText = state.srcMode === 'paste' && !!$('#in-text').value.trim();
  if (!hasUpload && !hasText) {
    state.lastRun = null;
    $('#result-card').classList.add('show');
    $('#result-hint').textContent = state.srcMode === 'upload' ? 'Choose a file first' : 'Add evidence first';
    $('#result-a').innerHTML = `<p class="inline-error">${state.srcMode === 'upload' ? 'Choose a local file, or switch to Paste text.' : 'Paste an HTTP capture or select/upload an evidence artifact before running analysis.'}</p>`;
    $('#result-b').textContent = '';
    $('#verdict-row').style.display = 'none';
    return;
  }
  state.lastRun = null;
    $('#verdict-row').style.display = 'none';
    $('#result-hint').textContent = 'Preparing analysis…';
    $('#result-a').textContent = '';
  $('#result-b').textContent = '';
  $('#result-meta').textContent = '';
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Running…';
  $('#result-card').classList.add('show');
  $('#result-hint').textContent = 'Local inference in progress…';
  $('#result-a').innerHTML = '<div class="muted">Analyzing current input…</div>';
  $('#result-b').innerHTML = '';

  try {
    let body;
    if (state.srcMode === 'upload' && state.uploadedFile) {
      const fd = new FormData();
      fd.append('file', state.uploadedFile);
      fd.append('template_id', state.template);
      fd.append('model', $('#in-model').value);
      fd.append('artifact_type', 'auto');
      const r = await api(cross ? '/api/cross-check' : '/api/analyze', { method: 'POST', body: fd });
      paintResult(r, cross);
    } else {
      const sampleSel = $('#in-text').value.trim();
      body = {
        raw_text: sampleSel,
        filename: 'pasted.txt',
        artifact_type: 'auto',
        template_id: state.template,
        model: $('#in-model').value,
      };
      const r = await api(cross ? '/api/cross-check' : '/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      paintResult(r, cross);
    }
  } catch (e) {
    state.lastRun = null;
    $('#verdict-row').style.display = 'none';
    $('#result-hint').textContent = 'Could not analyze this input';
    $('#result-a').innerHTML = `<p style="color:var(--red)">${esc(e.message)}</p>`;
    $('#result-b').innerHTML = '';
  } finally {
    btn.disabled = false; btn.innerHTML = old;
  }
}
$('#btn-run').addEventListener('click', () => runAnalysis(false));
$('#btn-cross').addEventListener('click', () => runAnalysis(true));

function paintResult(r, cross) {
  state.lastRun = r;
  $('#result-split').style.gridTemplateColumns = cross ? '1fr 1fr' : '1fr';
  $('#result-b').style.display = cross ? '' : 'none';

  if (cross) {
    $('#result-a').innerHTML = renderMarkdown(r.qwen.response);
    $('#result-b').innerHTML = renderMarkdown(r.llama.response);
    $('#result-meta').innerHTML =
      `<span><b>Template</b> ${esc(r.template_title || r.template_id)}</span>` +
      `<span><b>qwen2.5:3b</b> ${r.qwen.eval_tok_s} tok/s &middot; ${r.qwen.eval_count} tok</span>` +
      `<span><b>llama3.2:3b</b> ${r.llama.eval_tok_s} tok/s &middot; ${r.llama.eval_count} tok</span>`;
    $('#result-hint').textContent = 'Side-by-side comparison';
  } else {
    $('#result-a').innerHTML = renderMarkdown(r.output);
    $('#result-meta').innerHTML =
      `<span><b>Template</b> ${esc(r.template_title || r.template_id)}</span>` +
      `<span><b>Model</b> ${esc(r.model)}</span>` +
      `<span><b>Speed</b> ${r.telemetry.eval_tok_s} tok/s</span>` +
      `<span><b>Generated</b> ${r.telemetry.eval_count} tokens</span>` +
      `<span><b>Context</b> ${r.telemetry.prompt_eval_count} tokens</span>` +
      `<span><b>Artifact</b> ${esc(r.filename)}</span>`;
    $('#result-hint').textContent = 'Done';
  }
  $('#verdict-row').style.display = '';
}

/* ---------- human verdict -> validation log ---------- */
$$('#verdict-row .btn').forEach(b => b.addEventListener('click', async () => {
  if (!state.lastRun) return;
  const verdict = b.dataset.verdict;
  const isCross = !!state.lastRun.qwen;
  const out = isCross ? state.lastRun.qwen.response : state.lastRun.output;
  try {
    await api('/api/validation-log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        phase: 'GUI Arena',
        claim: (out || '').slice(0, 220).replace(/\s+/g, ' '),
        model: isCross ? 'qwen2.5:3b' : state.lastRun.model,
        source: 'GUI Analyzer',
        check: 'Human Analyst Review',
        result: verdict,
        verdict,
      }),
    });
    b.closest('.actions').querySelector('.muted').textContent = `Logged as ${verdict}`;
  } catch (e) { alert('Could not log verdict: ' + e.message); }
}));

/* ---------- dashboard ---------- */
async function loadDashboard() {
  try {
    const h = await api('/api/health');
    $('#dot-ollama').className = 'dot ' + (h.ollama_connected ? 'ok' : 'bad');
    const qwenReady = !!h.core_models_ready?.['qwen2.5:3b'];
    const llamaReady = !!h.core_models_ready?.['llama3.2:3b'];
    $('#txt-ollama').textContent = !h.ollama_connected ? 'Ollama offline'
      : (qwenReady && llamaReady) ? 'Ollama ready · Qwen + Llama'
      : `Ollama online · ${[qwenReady ? 'Qwen' : '', llamaReady ? 'Llama' : ''].filter(Boolean).join(' + ') || 'models missing'}`;
    $('#kpi-prompts').textContent = h.stats.total_prompts;
    $('#kpi-challenges').textContent = h.stats.total_challenges;
    const v = h.stats.validation || {};
    $('#kpi-accuracy').textContent = (v.accuracy_pct ?? 0) + '%';
    $('#kpi-usable').textContent = 'usable: ' + (v.usable_pct ?? 0) + '%';
    $('#kpi-hallucination').textContent = (v.hallucination_pct ?? 0) + '%';
    $('#kpi-claims').textContent = 'claims: ' + (v.total ?? 0);
  } catch (e) {
    $('#dot-ollama').className = 'dot bad';
    $('#txt-ollama').textContent = 'Health check failed';
    $('#kpi-prompts').textContent = '—';
    $('#kpi-challenges').textContent = '—';
  }

  try {
    const b = await api('/api/benchmarks');
    const tasks = b.tasks || [];
    const labels = tasks.map(t => t.task_id);
    if (labels.length && !state.charts.tps) {
      state.charts.tps = new Chart($('#chart-tps'), {
        type: 'bar',
        data: {
          labels,
          datasets: [
            { label: 'qwen2.5:3b', data: tasks.map(t => t.qwen_gen_tps), backgroundColor: '#2f9e8f' },
            { label: 'llama3.2:3b', data: tasks.map(t => t.llama_gen_tps), backgroundColor: '#3b4a5e' },
          ],
        },
        options: baseChartOpts('tokens / sec'),
      });
      state.charts.score = new Chart($('#chart-score'), {
        type: 'bar',
        data: {
          labels,
          datasets: [
            { label: 'qwen2.5:3b', data: tasks.map(t => t.qwen_score), backgroundColor: '#2f9e8f' },
            { label: 'llama3.2:3b', data: tasks.map(t => t.llama_score), backgroundColor: '#3b4a5e' },
          ],
        },
        options: baseChartOpts('score / 5'),
      });
    }
  } catch (e) {
    $('#chart-tps').parentElement.innerHTML = `<div class="empty">Benchmark data unavailable: ${esc(e.message)}<br/><button class="btn sm" data-retry-dashboard>Retry</button></div>`;
    $('#chart-score').parentElement.innerHTML = `<div class="empty">Benchmark data unavailable</div>`;
    document.querySelectorAll('[data-retry-dashboard]').forEach(b => b.addEventListener('click', loadDashboard, {once:true}));
  }

  try {
    const c = await api('/api/challenges');
    state.challenges = c.challenges || [];
    const tb = $('#challenges-tbody');
    if (!state.challenges.length) { tb.innerHTML = '<tr><td colspan="6" class="empty">No challenges</td></tr>'; return; }
    tb.innerHTML = state.challenges.map(ch => {
      const ev = ch.evaluation;
      const ok = ev && (ev.correct || ev.status === 'correct');
      const badge = ev
        ? `<span class="tag ${ok ? 'ok' : 'warn'}">${ok ? 'correct' : 'review'}</span>`
        : '<span class="tag mute">not run</span>';
      return `<tr>
        <td>${esc(ch.suite)}</td>
        <td>${esc(ch.name)}</td>
        <td><code>${esc(ch.target_param || '')}</code></td>
        <td>${esc(ch.expected_vuln || '')}</td>
        <td>${badge}</td>
        <td><button class="btn sm" data-load="${esc(ch.id)}">Load</button></td>
      </tr>`;
    }).join('');
    tb.querySelectorAll('[data-load]').forEach(b => b.addEventListener('click', () => {
      const ch = state.challenges.find(x => x.id === b.dataset.load);
      if (!ch) return;
      $$('.nav-btn').forEach(x => x.classList.remove('active'));
      $$('.view').forEach(v => v.classList.remove('active'));
      $('.nav-btn[data-view="analyzer"]').classList.add('active');
      $('#view-analyzer').classList.add('active');
      $('#in-text').value = ch.sample_text || '';
      $('#result-hint').textContent = `Loaded challenge: ${ch.name}`;
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }));
  } catch (e) {
    $('#challenges-tbody').innerHTML = `<tr><td colspan="6" class="empty">Could not load challenges: ${esc(e.message)}</td></tr>`;
  }
}

function baseChartOpts(label) {
  return {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { labels: { color: '#4a5b6d', boxWidth: 12 } } },
    scales: {
      x: { ticks: { color: '#68798b', font: { size: 10 } }, grid: { color: '#e3e9f0' } },
      y: { beginAtZero: true, ticks: { color: '#68798b' }, grid: { color: '#e3e9f0' }, title: { display: true, text: label, color: '#68798b' } },
    },
  };
}

/* ---------- AD graph ---------- */
async function loadGraph() {
  if (state.cy) return;
  try {
    const g = await api('/api/ad-graph');
    const nodes = (g.nodes || []).map(n => ({
      data: { id: n.id, label: n.label || n.name || n.id, kind: n.kind || n.type || '' },
    }));
    const edges = (g.edges || []).map((e, i) => ({
      data: { id: e.id || `e${i}`, source: e.source, target: e.target, label: e.kind || e.type || '' },
    }));
    const hl = new Set(g.highlighted_nodes || []);
    const hlEdges = new Set(g.highlighted_edges || []);
    edges.forEach(e => { e.data.path = hlEdges.has(e.data.id); });
    nodes.forEach(n => { n.data.path = hl.has(n.data.id); });
    state.cy = cytoscape({
      container: $('#cy'),
      elements: [...nodes, ...edges],
      style: [
        { selector: 'node', style: {
          'background-color': '#ffffff', 'border-width': 2, 'border-color': '#8fa0b2',
          'label': 'data(label)', 'color': '#1c2b3a', 'font-size': 10,
          'text-wrap': 'wrap', 'text-max-width': 100, 'text-valign': 'bottom', 'text-margin-y': 5,
          'width': 34, 'height': 34 } },
        { selector: 'node[path]', style: { 'background-color': '#d9f1eb', 'border-color': '#0d8f7f', 'border-width': 3 } },
        { selector: 'edge', style: {
          'width': 1.2, 'line-color': '#cfd9e4', 'target-arrow-color': '#cfd9e4',
          'target-arrow-shape': 'triangle', 'curve-style': 'bezier' } },
        { selector: 'edge[path]', style: { 'width': 3, 'line-color': '#df8d26', 'target-arrow-color': '#df8d26', 'z-index': 10 } },
      ],
      layout: { name: 'cose', animate: false, padding: 40, nodeRepulsion: 7000, idealEdgeLength: 120 },
    });
    $('#graph-hint').textContent = `${(g.nodes || []).length} nodes · ${(g.edges || []).length} edges · orange = shortest paths`;
    state.cy.on('tap', 'node', ev => {
      const d = ev.target.data();
      $('#node-info').innerHTML = `<b>${esc(d.label)}</b><br/><span class="muted">id: ${esc(d.id)}${d.kind ? ' · ' + esc(d.kind) : ''}</span>`;
    });
  } catch (e) {
    $('#graph-hint').textContent = 'unavailable';
    $('#cy').innerHTML = `<div class="empty">${esc(e.message)}</div>`;
  }
}

/* ---------- reports ---------- */
async function loadReports() {
  $('#btn-cvss').disabled = false;
  $('#btn-cvss').onclick = async () => {
    const v = $('#cvss-vector').value.trim();
    if (!v) return;
    try {
      const r = await api('/api/cvss', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ vector: v }),
      });
      $('#cvss-out').innerHTML = `<span class="tag ${r.severity === 'Critical' || r.severity === 'High' ? 'bad' : 'warn'}">${esc(r.severity)}</span> <b>${r.base_score}</b>`;
    } catch (e) { $('#cvss-out').textContent = 'Invalid vector: ' + e.message; }
  };

  $$('[data-export]').forEach(b => b.onclick = async () => {
    b.disabled = true;
    $('#export-out').textContent = 'Building…';
    try {
      const target = b.dataset.export === 'report' ? 'human_report' : b.dataset.export;
      const r = await api('/api/report/export', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ target }),
      });
      $('#export-out').replaceChildren(...(r.files || []).map(f => {
        const a = document.createElement('a');
        a.href = f.url; a.target = '_blank'; a.rel = 'noopener noreferrer';
        a.textContent = f.label;
        return a;
      }).flatMap((a, i) => i ? [Object.assign(document.createElement('span'), {textContent:' · '}), a] : [a]));
    } catch (e) { $('#export-out').textContent = 'Export failed: ' + e.message; }
    finally { b.disabled = false; }
  });

  try {
    const d = await api('/api/report/diff');
    const s = d.stats || {};
    $('#diff-hint').textContent = `${s.word_similarity_pct ?? 0}% word similarity`;
    const rows = [
      ['AI draft words', s.ai_words], ['Human-edited words', s.human_words],
      ['Words added', s.added_words], ['Words removed', s.removed_words],
      ['Replaced (AI side)', s.replaced_ai_words], ['Replaced (human side)', s.replaced_human_words],
      ['Line similarity', (s.line_similarity_pct ?? 0) + '%'],
    ];
    const pocs = (d.pocs || []).map(p =>
      `<figure style="margin:0;"><img src="${p.url}" style="width:100%;border-radius:8px;border:1px solid var(--line);" /><figcaption class="muted" style="font-size:11px;margin-top:4px;">${esc(p.name)}</figcaption></figure>`
    ).join('');
    $('#diff-out').innerHTML =
      `<table class="data" style="margin-bottom:14px;">${rows.map(r => `<tr><td class="muted">${r[0]}</td><td><b>${r[1] ?? '—'}</b></td></tr>`).join('')}</table>` +
      (pocs ? `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px;">${pocs}</div>` : '<div class="empty">No PoC images</div>');
    $('#poc-gallery').innerHTML = pocs || '<div class="empty">No PoC images</div>';
  } catch (e) {
    $('#diff-out').innerHTML = `<div class="empty">${esc(e.message)}</div>`;
    $('#poc-gallery').innerHTML = '';
  }
}

/* ---------- port solver ---------- */
$('#btn-solve').addEventListener('click', async () => {
  const url = $('#solve-url').value.trim();
  const description = $('#solve-desc').value.trim();
  const allowStateChanges = $('#solve-consent').checked;
  if (!url) { $('#solve-hint').textContent = 'Enter your lab instance URL first.'; return; }
  if (!allowStateChanges) {
    const proceed = window.confirm('Run only passive observation and generate proposed steps? No state-changing requests will be sent. Check the consent box to permit bounded POST/state-changing lab requests.');
    if (!proceed) return;
  }
  const btn = $('#btn-solve');
  const old = btn.innerHTML;
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Solving…';
  $('#solve-result').classList.add('show');
    $('#solve-hint').textContent = allowStateChanges ? 'Running bounded lab actions…' : 'Passive observation only; generating proposed steps…';
  try {
    const r = await api('/api/port-solver/solve', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url, description, allow_state_changes: allowStateChanges }),
    });
    const stateLabels = {
      solved: 'SOLVED · official confirmation', already_solved: 'Already solved · official confirmation',
      attempted: 'Attempted · not confirmed', not_solved: 'Not solved', expired: 'Lab expired/unavailable',
      blocked: 'Blocked by server/policy', unsupported: 'Unsupported lab type', model_error: 'Local model error',
    };
    $('#solve-hint').textContent = stateLabels[r.status] || 'Unconfirmed';
    $('#solve-meta').innerHTML = [
      `<span><b>Lab</b> ${esc(r.title || r.lab_type)}</span>`,
      `<span><b>Type</b> ${esc(r.lab_type)}</span>`,
      `<span><b>State</b> ${esc(r.status || 'unknown')}</span>`,
      `<span><b>Engine</b> ${esc(r.source || 'agentic')}</span>`,
      `<span><b>Confidence</b> ${esc(r.confidence || 'unknown')}</span>`,
      r.hypothesis ? `<span><b>Current hypothesis</b> ${esc(r.hypothesis)}</span>` : '',
      `<span><b>POST consent</b> ${r.state_changes_allowed ? 'granted for this run' : 'off (passive only)'}</span>`,
      `<span><b>HTTP</b> ${r.http_status}</span>`,
      `<span><b>Method</b> ${esc(r.method)}</span>`,
    ].join('');

    const reqRows = (r.requests || []).map(x =>
      `<tr><td>${esc(x.step)}</td><td>${esc(x.url)}</td><td>${x.status}</td><td>${x.length}</td></tr>`
    ).join('');
    const stepsTitle = r.solved ? 'Verified solution steps' : 'Suggested next steps (not verified)';

    $('#solve-body').innerHTML = `
      <div style="padding:12px 14px;border-radius:9px;margin-bottom:14px;">
        <div style="font-weight:700;color:${r.solved ? 'var(--green)' : (r.status === 'expired' || r.status === 'blocked' ? 'var(--red)' : 'var(--amber)')};margin-bottom:6px;">
          ${r.solved ? '&#10003; Lab solved — official confirmation' : r.status === 'expired' ? 'Lab unavailable or expired — no solve claim made' : r.status === 'blocked' ? 'Request blocked by lab or safety policy — no solve claim made' : r.status === 'attempted' ? 'Requests attempted, but no official solve confirmation observed' : r.status === 'model_error' ? 'Local model unavailable or returned an error' : 'No sufficiently grounded action was identified — no solve claim made'}
        </div>
        <div class="muted">${esc(r.explanation)}</div>
      </div>
      ${(r.steps && r.steps.length) ? `
      <div class="card" style="box-shadow:none;margin-bottom:14px;border-left:3px solid var(--teal);">
        <h3>${stepsTitle} <span class="hint">grounded in observed evidence</span></h3>
        <ol style="margin:0;padding-left:22px;line-height:1.75;">
          ${r.steps.map(s => `<li style="margin-bottom:7px;">${esc(s)}</li>`).join('')}
        </ol>
      </div>` : ''}
      <div class="card" style="box-shadow:none;margin-bottom:14px;">
        <h3>Solving payload</h3>
        <div style="font-family:Consolas,monospace;font-size:13px;background:var(--paper);padding:12px;border-radius:8px;">${esc(r.payload || '—')}</div>
      </div>
      <div class="card" style="box-shadow:none;margin-bottom:14px;">
        <h3>Response evidence</h3>
        <pre style="background:var(--paper);padding:12px;border-radius:8px;white-space:pre-wrap;font-size:12.5px;">${esc(r.evidence)}</pre>
      </div>
      <div class="card" style="box-shadow:none;">
        <h3>Requests sent</h3>
        <table class="data"><thead><tr><th>Step</th><th>URL</th><th>Status</th><th>Bytes</th></tr></thead><tbody>${reqRows}</tbody></table>
      </div>`;
  } catch (e) {
    $('#solve-hint').textContent = 'Error';
    $('#solve-body').innerHTML = `<p style="color:var(--red)">${esc(e.message)}</p>`;
  } finally { btn.disabled = false; btn.innerHTML = old; }
});

/* ---------- boot ---------- */
loadDashboard();