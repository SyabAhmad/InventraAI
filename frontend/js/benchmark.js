/* InventraAI — Benchmarking view
   Shows models from .env, 20 prompts, Start button, and live progress.
   Polls GET /api/benchmark/jobs/{id} while the background job runs. */
(function () {
  'use strict';

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function apiBase() { return window.appApiBase ? window.appApiBase() : ''; }

  var pollTimer = null;
  var currentJobId = null;

  function stopPoll() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  }

  function renderSkeletons() {
    $('content').innerHTML = `
      <div class="section">
        <h2>Benchmarking — Cost-Efficient Optimization of Open-Source LLM Agents</h2>
        <p class="sub">Pick models (from <code>.env → LLM_BENCHMARK_MODELS</code>) and prompts, choose a <strong>mode</strong> (Baseline = original prompt · Optimized = shorter context), then press Start. Progress streams below row-by-row. Every run saves date + model tag + hardware + settings + case ID + output + latency/tokens + errors to <code>benchmark_results/</code> (FYP Roadmap §5).</p>
      </div>
      <div class="section" id="bench-config"><div class="empty">Loading models & prompts from backend…</div></div>
      <div class="section" id="bench-controls"></div>
      <div class="section" id="bench-progress" style="display:none">
        <div class="bench-progress-head"><strong id="bench-status">Running…</strong><span id="bench-count" class="sub"></span></div>
        <div class="bench-progress"><div id="bench-bar" class="bench-bar"></div></div>
        <div id="bench-live" class="sub" style="margin-top:6px"></div>
      </div>
      <div class="section" id="bench-charts" style="display:none">
        <h3>Charts <span class="sub">(built after all runs finish — print-ready for viva)</span></h3>
        <p class="sub" id="bench-charts-note">Charts will appear here when processing is complete.</p>
        <div class="bench-chart-grid">
          <div class="card chart-card"><div class="chart-box"><canvas id="bench-chart-success"></canvas></div><div class="sub" id="bench-chart-success-note">Task success & tool accuracy per model</div></div>
          <div class="card chart-card"><div class="chart-box"><canvas id="bench-chart-latency"></canvas></div><div class="sub" id="bench-chart-latency-note">Median latency per model (lower = better)</div></div>
          <div class="card chart-card"><div class="chart-box"><canvas id="bench-chart-steps"></canvas></div><div class="sub" id="bench-chart-steps-note">Avg LLM steps per model (fewer = cheaper)</div></div>
        </div>
      </div>
      <div class="section" id="bench-summary" style="display:none"></div>
      <div class="section" id="bench-table-wrap" style="display:none">
        <h3>Live results <span class="sub">(newest last — scrolls down as it runs)</span></h3>
        <table>
          <thead><tr><th>#</th><th>Model</th><th>Prompt</th><th>Status</th><th class="num">Latency</th><th class="num">Steps</th><th class="num">Tokens*</th><th class="num">Forecast MAE/MAPE</th><th>Tools</th><th>Answer</th></tr></thead>
          <tbody id="bench-rows"></tbody>
        </table>
        <p class="sub">* tokens = chars ÷ 4 proxy (provider usage not always returned) + steps = LLM calls. Forecast MAE/MAPE is ground-truth from SQLite validation, shown for p10–p12.</p>
      </div>`;
  }

  function renderConfig(cfg) {
    var models = cfg.models && cfg.models.length ? cfg.models : [cfg.default_model || 'no model'];
    var prompts = cfg.prompts || [];
    var meta = cfg.metadata || {};
    var metaLine = [meta.platform, meta.python ? 'Python ' + meta.python : '', meta.temperature != null ? 'temp=' + meta.temperature : ''].filter(Boolean).join(' · ');

    $('bench-config').innerHTML = `
      <div class="cards">
        ${card('Models in .env', models.length, esc(cfg.provider || '') + ' · ' + esc(cfg.base_url || ''))}
        ${card('Benchmark prompts', prompts.length, 'Frozen suite (never change between modes)')}
        ${card('Default model', esc(cfg.default_model || '—'), esc(metaLine || 'LLM_MODEL'))}
      </div>
      <h3>Models <span class="sub">(from .env → LLM_BENCHMARK_MODELS = ${esc(models.join(', '))})</span></h3>
      <div class="bench-models" id="bench-models">
        ${models.map(function (m, i) {
          return `<label class="bench-check"><input type="checkbox" class="bench-model" value="${esc(m)}" ${i < 2 ? 'checked' : 'checked'}> <code>${esc(m)}</code></label>`;
        }).join('')}
      </div>
      <h3 style="margin-top:16px">Prompts <span class="sub">(${prompts.length} — uncheck to skip · smoke = tick only p01–p05)</span></h3>
      <div class="bench-prompts">
        ${prompts.map(function (p) {
          return `<label class="bench-check bench-prompt"><input type="checkbox" class="bench-prompt-check" value="${esc(p.id)}" checked> <strong>${esc(p.id)}</strong> ${esc(p.question)} <span class="sub">[${esc(p.category)} · expects: ${esc((p.expected_tools || []).join(', '))}]</span></label>`;
        }).join('')}
      </div>`;

    $('bench-controls').innerHTML = `
      <div class="bench-controls">
        <button id="bench-start" class="btn-primary">▶ Start Benchmark</button>
        <label class="sub">Mode
          <select id="bench-mode" style="margin-left:4px">
            <option value="baseline">Baseline (original)</option>
            <option value="optimized">Optimized (shorter)</option>
          </select></label>
        <label class="sub">Repeats <input type="number" id="bench-repeats" min="1" max="5" value="${cfg.repeats_default || 1}" style="width:56px;margin-left:4px"></label>
        <button id="bench-select-all" class="btn-ghost">Select all</button>
        <button id="bench-smoke" class="btn-ghost">Smoke only (p01–p05)</button>
        <a id="bench-export" href="#" class="btn-ghost btn-download" style="display:none" download title="Download the Excel report with charts">⬇ Download Excel</a>
        <span id="bench-msg" class="sub"></span>
      </div>
      <p class="sub" style="margin-top:6px">Note: 20 prompts × 5 cloud models takes a while (each prompt = 1 LLM call + tools, incl. network). You can watch every row land live below. <strong>Baseline vs Optimized:</strong> run the same models + prompts twice (once per mode), then compare accuracy vs latency — that's the cost-efficiency evidence (Roadmap T17).</p>`;

    $('bench-start').addEventListener('click', startRun);
    $('bench-select-all').addEventListener('click', function () {
      document.querySelectorAll('.bench-prompt-check').forEach(function (c) { c.checked = true; });
    });
    $('bench-smoke').addEventListener('click', function () {
      document.querySelectorAll('.bench-prompt-check').forEach(function (c) {
        c.checked = ['p01','p02','p03','p04','p05'].indexOf(c.value) !== -1;
      });
    });
  }

  function card(label, value, hint) {
    return `<div class="card"><div class="label">${label}</div><div class="value" style="font-size:18px">${value}</div><div class="hint">${hint}</div></div>`;
  }

  function startRun() {
    stopPoll();
    var models = Array.from(document.querySelectorAll('.bench-model:checked')).map(function (c) { return c.value; });
    var promptIds = Array.from(document.querySelectorAll('.bench-prompt-check:checked')).map(function (c) { return c.value; });
    var repeats = Math.max(1, Math.min(5, parseInt($('bench-repeats').value, 10) || 1));
    var modeEl = $('bench-mode');
    var mode = modeEl ? modeEl.value : 'baseline';
    var msg = $('bench-msg');
    if (!models.length) { msg.textContent = 'Pick at least 1 model.'; return; }
    if (!promptIds.length) { msg.textContent = 'Pick at least 1 prompt.'; return; }
    if (window.APP_MODE !== 'live') { msg.textContent = 'Backend offline — start with uvicorn src.api.main:app to run live benchmarks.'; return; }

    msg.textContent = `Starting ${mode} · ${models.length} model(s) × ${promptIds.length} prompt(s) × ${repeats} repeat(s)…`;
    $('bench-start').disabled = true;
    destroyCharts();
    var exportA = $('bench-export');
    if (exportA) { exportA.style.display = 'none'; }
    var chartNote = $('bench-charts-note');
    if (chartNote) chartNote.textContent = 'Charts will appear here when processing is complete.';
    $('bench-progress').style.display = '';
    $('bench-charts').style.display = 'none';
    $('bench-table-wrap').style.display = '';
    $('bench-summary').style.display = 'none';
    $('bench-rows').innerHTML = '';
    $('bench-bar').style.width = '0%';
    $('bench-status').textContent = 'Starting…';
    $('bench-live').textContent = '';

    fetch(apiBase() + '/api/benchmark/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ models: models, prompt_ids: promptIds, repeats: repeats, mode: mode })
    }).then(function (r) {
      if (!r.ok) return r.json().then(function (j) { throw new Error(j.detail || ('HTTP ' + r.status)); });
      return r.json();
    }).then(function (j) {
      currentJobId = j.job_id;
      msg.textContent = 'Job started: ' + j.job_id;
      poll();
      pollTimer = setInterval(poll, 1200);
    }).catch(function (err) {
      msg.textContent = 'Error: ' + err.message;
      $('bench-start').disabled = false;
    });
  }

  function poll() {
    if (!currentJobId) return;
    fetch(apiBase() + '/api/benchmark/jobs/' + encodeURIComponent(currentJobId))
      .then(function (r) { return r.json(); })
      .then(function (job) {
        var pct = job.progress_pct || 0;
        $('bench-bar').style.width = pct + '%';
        $('bench-status').textContent = job.status === 'done' ? 'Done ✓' : (job.status === 'failed' ? 'Failed ✗' : 'Running… ' + pct + '%');
        $('bench-count').textContent = (job.done || 0) + '/' + (job.total || '…') + ' runs' + (job.current_prompt ? ' — ' + job.current_prompt : '');
        $('bench-live').textContent = job.current_model ? 'Model: ' + job.current_model : '';
        renderRows(job);
        renderSummary(job);
        var exportA = $('bench-export');
        if (exportA && job.results && job.results.length) {
          exportA.style.display = '';
          exportA.href = apiBase() + '/api/benchmark/export/' + encodeURIComponent(job.id);
        }
        var finished = job.status === 'done' || job.status === 'failed';
        if (finished) {
          stopPoll();
          var btn = $('bench-start');
          if (btn) btn.disabled = false;
          if (exportA) exportA.href = apiBase() + '/api/benchmark/export/' + encodeURIComponent(job.id);
          renderCharts(job);
          var chartNote = $('bench-charts-note');
          if (chartNote) chartNote.textContent = 'All runs finished — charts built from the final evidence.';
          if (job.file) $('bench-live').textContent = 'Saved to ' + job.file;
        }
      })
      .catch(function (err) {
        $('bench-live').textContent = 'Poll error: ' + err.message;
      });
  }

  var chartCharts = [];
  function destroyCharts() {
    chartCharts.forEach(function (c) { try { c.destroy(); } catch (e) { /* ignore */ } });
    chartCharts = [];
  }

  function renderCharts(job) {
    var summary = job.summary || {};
    var models = Object.keys(summary);
    var block = $('bench-charts');
    if (!block) return;
    if (!models.length || typeof Chart === 'undefined') { block.style.display = 'none'; return; }
    block.style.display = '';
    destroyCharts();
    var labels = models;
    var success = models.map(function (m) { return summary[m].success_rate || 0; });
    var accuracy = models.map(function (m) { return summary[m].tool_accuracy || 0; });
    var medianLat = models.map(function (m) { return summary[m].median_latency_ms || summary[m].avg_latency_ms || 0; });
    var steps = models.map(function (m) { return summary[m].avg_steps || 0; });
    var tick = '#6b6b6b';
    var grid = 'rgba(227,221,209,.6)';
    var opts = function (yTitle) {
      return {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: tick, font: { size: 11 } } } },
        scales: {
          x: { ticks: { color: tick }, grid: { color: grid } },
          y: { beginAtZero: true, title: { display: true, text: yTitle || '' }, ticks: { color: tick }, grid: { color: grid } },
        },
      };
    };
    var mk = function (id, cfg) {
      var el = $(id);
      if (el) chartCharts.push(new Chart(el.getContext('2d'), cfg));
    };
    mk('bench-chart-success', {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          { label: 'Task success %', data: success, backgroundColor: 'rgba(58,125,68,.7)', borderColor: '#3a7d44', borderWidth: 1 },
          { label: 'Tool accuracy %', data: accuracy, backgroundColor: 'rgba(139,111,71,.7)', borderColor: '#8b6f47', borderWidth: 1 },
        ],
      },
      options: opts('%'),
    });
    mk('bench-chart-latency', {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{ label: 'Median latency (ms)', data: medianLat, backgroundColor: 'rgba(192,57,43,.65)', borderColor: '#c0392b', borderWidth: 1 }],
      },
      options: opts('ms'),
    });
    mk('bench-chart-steps', {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{ label: 'Avg steps', data: steps, backgroundColor: 'rgba(184,134,11,.65)', borderColor: '#b8860b', borderWidth: 1 }],
      },
      options: opts('steps'),
    });
  }

  function renderRows(job) {
    var rows = job.results || [];
    var tbody = $('bench-rows');
    if (!tbody) return;
    tbody.innerHTML = rows.map(function (r, i) {
      var cls = r.status === 'error' ? 'bench-fail' : (r.tool_accuracy && r.success ? 'bench-pass' : 'bench-warn');
      var tools = (r.tools_called || []).map(function (t) { return `<span class="bench-tool">${esc(t)}</span>`; }).join(' ');
      var preview = esc((r.answer_preview || r.error || '').slice(0, 140));
      var fm = r.forecast_metrics || {};
      var fmCell = (fm.mae != null) ? (fm.mae + ' / ' + (fm.mape != null ? fm.mape + '%' : '—')) : '<span class="sub">—</span>';
      return `<tr><td>${i + 1}</td><td><code>${esc(r.model)}</code>${r.mode ? `<br><span class="sub">${esc(r.mode)}</span>` : ''}</td><td><strong>${esc(r.id)}</strong> ${esc(r.question)} ${r.repeat && r.repeat > 1 ? `<span class="sub">r${r.repeat}</span>` : ''}</td><td><span class="status ${cls}">${esc(r.status)}</span></td><td class="num">${r.latency_ms} ms</td><td class="num">${r.steps}</td><td class="num">${r.tokens_proxy != null ? r.tokens_proxy : '—'}</td><td class="num">${fmCell}</td><td>${tools || '<span class="sub">—</span>'}</td><td class="sub" style="max-width:280px">${preview}</td></tr>`;
    }).join('');
    // keep latest visible
    var wrap = $('bench-table-wrap');
    if (wrap) wrap.scrollTop = wrap.scrollHeight;
  }

  function renderSummary(job) {
    var summary = job.summary || {};
    var models = Object.keys(summary);
    if (!models.length) return;
    var mode = job.mode ? ' · mode: <strong>' + esc(job.mode) + '</strong>' : '';
    $('bench-summary').style.display = '';
    $('bench-summary').innerHTML = `
      <h3>Summary so far <span class="sub">(accumulated live${mode})</span></h3>
      <table>
        <thead><tr><th>Model</th><th class="num">Runs</th><th class="num">Success rate</th><th class="num">Tool accuracy</th><th class="num">Median latency</th><th class="num">p95 latency</th><th class="num">Avg steps</th><th class="num">Avg tokens*</th><th class="num">Forecast MAE</th><th class="num">MAPE</th></tr></thead>
        <tbody>${models.map(function (m) {
          var s = summary[m];
          var mae = s.forecast_mae != null ? s.forecast_mae : '—';
          var mape = s.forecast_mape != null ? s.forecast_mape + '%' : '—';
          return `<tr><td><code>${esc(m)}</code></td><td class="num">${s.total || 0}</td><td class="num">${s.success_rate || 0}%</td><td class="num">${s.tool_accuracy || 0}%</td><td class="num">${s.median_latency_ms != null ? s.median_latency_ms : s.avg_latency_ms} ms</td><td class="num">${s.p95_latency_ms || 0} ms</td><td class="num">${s.avg_steps || 0}</td><td class="num">${s.avg_tokens || 0}</td><td class="num">${mae}</td><td class="num">${mape}</td></tr>`;
        }).join('')}</tbody>
      </table>
      <p class="sub" style="margin-top:6px">Viva line: → lower median/p95 latency + fewer steps with similar accuracy = more cost-efficient. Run Baseline and Optimized with the same models/cases and compare accuracy vs latency. Full evidence (date, hardware, settings, every row + errors) saved to <code>benchmark_results/</code>.</p>`;
  }

  function renderBenchmark() {
    stopPoll();
    renderSkeletons();
    if (window.APP_MODE !== 'live') {
      $('bench-config').innerHTML = '<div class="empty">Benchmarking needs the live backend. Start it with <code>uvicorn src.api.main:app</code> then reload.</div>';
      return;
    }
    window.appFetchJson('/api/benchmark/config', 8000).then(function (cfg) {
      renderConfig(cfg);
    }).catch(function (err) {
      $('bench-config').innerHTML = '<div class="empty">Could not load benchmark config: ' + esc(err.message) + '</div>';
    });
  }

  window.BenchmarkUI = { render: renderBenchmark };
})();
