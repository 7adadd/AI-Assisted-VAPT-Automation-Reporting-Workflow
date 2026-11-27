/* ============================================================
   AegisVAPT — Localhost-Only Controller
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
    if (/^\s*\|/.test(line)) continue;
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

function switchView(viewName) {
  $$('.nav-btn').forEach(b => {
    const isMatch = b.dataset.view === viewName;
    b.classList.toggle('active', isMatch);
    if (isMatch) b.setAttribute('aria-current', 'page');
    else b.removeAttribute('aria-current');
  });
  $$('.view').forEach(v => v.classList.toggle('active', v.id === 'view-' + viewName));
  if (viewName === 'dashboard') loadDashboard();
  if (viewName === 'graph') loadGraph();
  if (viewName === 'reports') loadReports();
}

/* ---------- navigation ---------- */
$$('.nav-btn').forEach(btn => btn.addEventListener('click', () => {
  switchView(btn.dataset.view);
}));

/* ---------- step 1: source mode ---------- */
function setSourceMode(mode) {
  state.srcMode = mode;
  $$('#src-seg button').forEach(x => {
    const on = x.dataset.src === mode;
    x.classList.toggle('on', on);
    x.setAttribute('aria-pressed', on ? 'true' : 'false');
  });
  $('#src-paste').style.display  = mode === 'paste'  ? '' : 'none';
  $('#src-upload').style.display = mode === 'upload' ? '' : 'none';
  $('#src-url').style.display    = mode === 'url'    ? '' : 'none';
}

$$('#src-seg button').forEach(b => b.addEventListener('click', () => setSourceMode(b.dataset.src)));

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
function selectTemplate(tpl) {
  state.template = tpl;
  $$('#review-grid .review-card').forEach(x => {
    const on = x.dataset.tpl === tpl;
    x.classList.toggle('on', on);
    x.setAttribute('aria-pressed', on ? 'true' : 'false');
  });
}

$$('#review-grid .review-card').forEach(c => c.addEventListener('click', () => selectTemplate(c.dataset.tpl)));

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
    $('#in-text').value = r.context;
    $('#result-hint').textContent = '';
    dropZone.innerHTML = `<b>${esc(r.origin)}</b><br/><span class="muted">${r.pages_fetched} pages &middot; ${r.query_params.length} params &middot; ${r.form_count} forms</span>`;
    state.uploadedFile = null;
    setSourceMode('paste');
    selectTemplate('PS1');
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
      const body = {
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
        source: 'AegisVAPT Analyzer',
        check: 'Human Analyst Review',
        result: verdict,
        verdict,
      }),
    });
    b.closest('.actions').querySelector('.muted').textContent = `Logged as ${verdict}`;
    loadHealthBadge();
  } catch (e) { alert('Could not log verdict: ' + e.message); }
}));

/* ---------- health badge + KPI summary (safe when dashboard is hidden) ---------- */
async function loadHealthBadge() {
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
}

/* ---------- dashboard ---------- */
async function loadDashboard() {
  await loadHealthBadge();

  if ($('#view-dashboard').classList.contains('active')) {
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
              { label: 'qwen2.5:3b', data: tasks.map(t => t.qwen_gen_tps), backgroundColor: '#0d9488', borderRadius: 4 },
              { label: 'llama3.2:3b', data: tasks.map(t => t.llama_gen_tps), backgroundColor: '#1e3a5f', borderRadius: 4 },
            ],
          },
          options: baseChartOpts('tokens / sec'),
        });
        state.charts.score = new Chart($('#chart-score'), {
          type: 'bar',
          data: {
            labels,
            datasets: [
              { label: 'qwen2.5:3b', data: tasks.map(t => t.qwen_score), backgroundColor: '#0d9488', borderRadius: 4 },
              { label: 'llama3.2:3b', data: tasks.map(t => t.llama_score), backgroundColor: '#1e3a5f', borderRadius: 4 },
            ],
          },
          options: baseChartOpts('score / 5', 5),
        });
      } else if (state.charts.tps && state.charts.score) {
        state.charts.tps.resize();
        state.charts.tps.update();
        state.charts.score.resize();
        state.charts.score.update();
      }
    } catch (e) {
      $('#chart-tps').parentElement.innerHTML = `<div class="empty">Benchmark data unavailable: ${esc(e.message)}<br/><button class="btn sm" data-retry-dashboard>Retry</button></div>`;
      $('#chart-score').parentElement.innerHTML = `<div class="empty">Benchmark data unavailable</div>`;
      document.querySelectorAll('[data-retry-dashboard]').forEach(btn => btn.addEventListener('click', loadDashboard, {once:true}));
    }
  }

  try {
    const c = await api('/api/challenges');
    state.challenges = c.challenges || [];
    const tb = $('#challenges-tbody');
    if (!state.challenges.length) { tb.innerHTML = '<tr><td colspan="6" class="empty">No challenges</td></tr>'; return; }
    tb.innerHTML = state.challenges.map(ch => {
      const ev = ch.evaluation;
      const ok = ev && (ev.passed === true || ev.correct === true || ev.status === 'correct');
      const tps = ev && ev.gen_tps ? ` &middot; ${Number(ev.gen_tps).toFixed(0)} t/s` : '';
      const badge = ev
        ? `<span class="tag ${ok ? 'ok' : 'warn'}">${ok ? 'passed' + tps : 'review'}</span>`
        : '<span class="tag mute">not run</span>';
      return `<tr>
        <td><b>${esc(ch.suite)}</b></td>
        <td>${esc(ch.name)}</td>
        <td><code>${esc(ch.target_param || '')}</code></td>
        <td>${esc(ch.expected_vuln || '')}</td>
        <td>${badge}</td>
        <td><button class="btn sm" data-load="${esc(ch.id)}">Load</button></td>
      </tr>`;
    }).join('');
    tb.querySelectorAll('[data-load]').forEach(btn => btn.addEventListener('click', () => {
      const ch = state.challenges.find(x => x.id === btn.dataset.load);
      if (!ch) return;
      switchView('analyzer');
      setSourceMode('paste');
      selectTemplate(ch.recommended_template || 'W1');
      $('#in-text').value = ch.sample_text || '';
      $('#result-card').classList.add('show');
      $('#result-hint').textContent = `Loaded challenge: ${ch.name}`;
      $('#result-meta').textContent = '';
      $('#result-a').innerHTML = `<div class="muted">Challenge <b>${esc(ch.name)}</b> loaded into Step 1. Click <b>Run analysis</b> to execute local inference.</div>`;
      $('#result-b').style.display = 'none';
      $('#verdict-row').style.display = 'none';
      $('.main').scrollTo({ top: 0, behavior: 'smooth' });
    }));
  } catch (e) {
    $('#challenges-tbody').innerHTML = `<tr><td colspan="6" class="empty">Could not load challenges: ${esc(e.message)}</td></tr>`;
  }
}

function baseChartOpts(label, maxVal) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: { legend: { labels: { color: '#47586b', boxWidth: 12, font: { weight: '600' } } } },
    scales: {
      x: { ticks: { color: '#5b6c80', font: { size: 11, weight: '600' } }, grid: { display: false } },
      y: {
        beginAtZero: true,
        ...(maxVal ? { suggestedMax: maxVal } : {}),
        ticks: { color: '#5b6c80' },
        grid: { color: '#e2e8f0' },
        title: { display: true, text: label, color: '#5b6c80', font: { size: 11 } },
      },
    },
  };
}

/* ---------- AD graph ---------- */
async function loadGraph() {
  if (state.cy) {
    state.cy.resize();
    state.cy.fit(undefined, 36);
    return;
  }
  try {
    const g = await api('/api/ad-graph');
    const hl = new Set(g.highlighted_nodes || []);
    const hlEdges = new Set(g.highlighted_edges || []);
    const nodes = (g.nodes || []).map(n => ({
      data: {
        id: n.id,
        label: n.label || n.name || n.id,
        kind: n.kind || n.type || 'Entity',
        path: hl.has(n.id),
      },
    }));
    const edges = (g.edges || []).map((e, i) => {
      const id = e.id || `e${i}`;
      return {
        data: {
          id,
          source: e.source,
          target: e.target,
          label: e.label || e.right || e.relationship || e.kind || e.type || '',
          path: hlEdges.has(id),
        },
      };
    });
    state.cy = cytoscape({
      container: $('#cy'),
      elements: [...nodes, ...edges],
      style: [
        { selector: 'node', style: {
          'background-color': '#ffffff',
          'border-width': 2,
          'border-color': '#94a3b8',
          'label': 'data(label)',
          'color': '#1e293b',
          'font-size': 10,
          'font-weight': 600,
          'text-wrap': 'wrap',
          'text-max-width': 130,
          'text-valign': 'bottom',
          'text-margin-y': 6,
          'text-background-color': '#f2f6fa',
          'text-background-opacity': 0.85,
          'text-background-padding': '2px',
          'width': 32,
          'height': 32 } },
        { selector: 'node[?path]', style: {
          'background-color': '#d1fae5',
          'border-color': '#0d9488',
          'border-width': 3,
          'width': 36,
          'height': 36 } },
        { selector: 'edge', style: {
          'width': 1.6,
          'line-color': '#cbd5e1',
          'target-arrow-color': '#94a3b8',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'label': 'data(label)',
          'font-size': 9,
          'color': '#475569',
          'text-background-color': '#f2f6fa',
          'text-background-opacity': 0.92,
          'text-background-padding': '2px',
          'text-rotation': 'autorotate' } },
        { selector: 'edge[?path]', style: {
          'width': 3.2,
          'line-color': '#d97706',
          'target-arrow-color': '#d97706',
          'color': '#92400e',
          'font-weight': 700,
          'z-index': 10 } },
      ],
      layout: {
        name: 'breadthfirst',
        directed: true,
        animate: false,
        padding: 38,
        spacingFactor: 1.55,
        avoidOverlap: true,
      },
    });
    state.cy.fit(undefined, 36);
    const pathCount = Object.values(g.ground_truth?.paths_to_highvalue || {}).filter(p => Array.isArray(p) && p.length).length;
    $('#graph-hint').textContent = `${nodes.length} nodes · ${edges.length} edges · ${pathCount} shortest paths`;
    state.cy.on('tap', 'node', ev => {
      const node = ev.target;
      const d = node.data();
      const outEdges = node.outgoers('edge').map(ed => `${ed.data('label')} -> ${ed.target().data('label')}`);
      const inEdges = node.incomers('edge').map(ed => `${ed.source().data('label')} -> ${ed.data('label')}`);
      const pathBadge = d.path ? '<span class="tag ok">On BFS Shortest Path</span>' : '<span class="tag mute">Not on shortest path</span>';
      $('#node-info').innerHTML =
        `<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px;">` +
        `<b style="color:var(--ink);font-size:14px;">${esc(d.label)}</b>` +
        `<span class="tag warn">${esc(d.kind)}</span>${pathBadge}</div>` +
        `<div class="muted">ID: <code>${esc(d.id)}</code></div>` +
        (inEdges.length ? `<div class="muted" style="margin-top:6px;"><b>Inbound:</b> ${esc(inEdges.join(' | '))}</div>` : '') +
        (outEdges.length ? `<div class="muted" style="margin-top:4px;"><b>Outbound:</b> ${esc(outEdges.join(' | '))}</div>` : '');
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
      ['Words inserted (net)', s.added_words], ['Words deleted', s.removed_words],
      ['Replaced (AI -> Human)', `${s.replaced_ai_words ?? '—'} -> ${s.replaced_human_words ?? '—'}`],
      ['Line-level similarity', (s.line_similarity_pct ?? 0) + '%'],
    ];
    const diffSnippet = (d.unified_diff_lines || []).slice(0, 60).join('\n');
    $('#diff-out').innerHTML =
      `<table class="data">${rows.map(r => `<tr><td class="muted">${r[0]}</td><td><b>${r[1] ?? '—'}</b></td></tr>`).join('')}</table>` +
      (diffSnippet ? `<details style="margin-top:12px;"><summary class="muted" style="cursor:pointer;font-weight:600;">Show unified diff excerpt</summary><pre style="max-height:240px;overflow:auto;margin-top:8px;background:var(--paper);padding:11px;border-radius:8px;border:1px solid var(--line);font-size:11.5px;color:var(--ink);">${esc(diffSnippet)}</pre></details>` : '');

    const pocs = (d.pocs || []).map(p =>
      `<a class="poc-card" href="${p.url}" target="_blank" rel="noopener noreferrer">` +
      `<img src="${p.url}" alt="${esc(p.name)}" />` +
      `<div class="poc-cap">${esc(p.name)}</div></a>`
    ).join('');
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
loadHealthBadge();