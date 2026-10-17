/* InventraAI — Chat view (ChatGPT-style) with persistent conversation history.
   Live mode: questions go to the FastAPI backend and run through the LangGraph
   agent (real tool-calling over live SQLite data).
   Snapshot mode (backend offline): answers come from the local intent engine
   so the static dashboard stays usable. No fabricated data either way. */
(function () {
  'use strict';

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function money(n) { return '$' + Number(n).toFixed(2); }

  /* Safe markdown: HTML is escaped BEFORE markdown parsing, so model output
     can never inject tags - only markdown constructs render. */
  function mdToHtml(text) {
    var raw = String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    if (window.marked && typeof window.marked.parse === 'function') {
      try {
        return window.marked.parse(raw, { breaks: true, gfm: true });
      } catch (e) { /* fall through to plain rendering */ }
    }
    return raw.replace(/\n/g, '<br>');
  }

  var D = null;
  var busy = false;

  /* ---------- conversation storage ---------- */
  var LS_CONVS = 'inventraai_chat_conversations';
  var LS_ACTIVE = 'inventraai_chat_active';

  function loadConvs() {
    try { return JSON.parse(localStorage.getItem(LS_CONVS)) || []; }
    catch (e) { return []; }
  }
  function saveConvs(convs) {
    localStorage.setItem(LS_CONVS, JSON.stringify(convs));
  }
  function getActiveConv() {
    var convs = loadConvs();
    var activeId = localStorage.getItem(LS_ACTIVE);
    for (var i = 0; i < convs.length; i++) {
      if (convs[i].id === activeId) return convs[i];
    }
    return createConv(convs);
  }
  function createConv(convs) {
    var conv = {
      id: 'c' + Date.now() + Math.floor(Math.random() * 1000),
      title: 'New conversation',
      messages: [],
      ts: Date.now()
    };
    convs.unshift(conv);
    saveConvs(convs);
    localStorage.setItem(LS_ACTIVE, conv.id);
    return conv;
  }
  function persist(conv) {
    var convs = loadConvs();
    for (var i = 0; i < convs.length; i++) {
      if (convs[i].id === conv.id) { convs[i] = conv; break; }
    }
    saveConvs(convs);
  }

  /* ---------- data helpers ---------- */
  function findProduct(t) {
    var m = t.match(/sku[- ]?(\d{3,4})/i);
    if (m) {
      var sku = 'SKU-' + ('0000' + m[1]).slice(-4);
      for (var i = 0; i < D.products.length; i++) {
        if (D.products[i].sku.toLowerCase() === sku.toLowerCase()) return D.products[i];
      }
    }
    for (var j = 0; j < D.products.length; j++) {
      if (t.indexOf(D.products[j].name.toLowerCase()) !== -1) return D.products[j];
    }
    return null;
  }
  function statusOf(p) {
    if (p.current_stock === 0) return 'out of stock';
    if (p.current_stock < p.min_stock_threshold) return 'low stock';
    return 'healthy';
  }

  /* ---------- intent engine ---------- */
  function answer(q) {
    if (!D) return 'Data not loaded. Run `python scripts/generate_products_html.py` first.';
    var t = q.toLowerCase().trim();

    if (/(how many|stock|units|available|inventory of)/.test(t)) {
      var p = findProduct(t);
      if (p) {
        return p.name + ' (' + p.sku + ')\n' +
          'Current stock: ' + p.current_stock + ' units\n' +
          'Minimum threshold: ' + p.min_stock_threshold + '\n' +
          'Status: ' + statusOf(p) + '\n' +
          'Price: ' + money(p.price) + ' · Category: ' + p.category + '\n' +
          'Units sold (all time): ' + (p.total_units_sold || 0);
      }
      if (/(low|below)/.test(t)) {
        var low = D.low_stock;
        if (!low.length) return 'No products are below their minimum stock level.';
        return low.length + ' products are in low stock:\n' +
          low.slice(0, 10).map(function (x) {
            return '• ' + x.name + ' (' + x.sku + ') — ' + x.current_stock + ' units (min ' + x.min_stock_threshold + ')';
          }).join('\n') + (low.length > 10 ? '\n… and ' + (low.length - 10) + ' more' : '');
      }
      if (/(out of stock|out-of-stock|zero)/.test(t)) {
        var out = D.out_of_stock;
        if (!out.length) return 'No products are out of stock.';
        return out.length + ' products are out of stock:\n' +
          out.map(function (x) { return '• ' + x.name + ' (' + x.sku + ')'; }).join('\n');
      }
    }

    if (/(summary|overview|how is inventory|total value)/.test(t)) {
      var s = D.summary;
      return 'Inventory summary\n' +
        '• Products: ' + s.total_products + '\n' +
        '• Total stock units: ' + s.total_stock_units.toLocaleString() + '\n' +
        '• Low stock: ' + s.low_stock_count + '\n' +
        '• Out of stock: ' + s.out_of_stock_count + '\n' +
        '• Inventory value: ' + money(s.inventory_value_at_price);
    }

    if (/(top|best|fast).*(sell|seller|moving)|top sellers/.test(t)) {
      if (!D.top_sellers.length) return 'No sales data yet.';
      return 'Top sellers by units sold:\n' +
        D.top_sellers.slice(0, 8).map(function (x, i) {
          return (i + 1) + '. ' + x.name + ' (' + x.category + ') — ' + x.total_units + ' units, ' + money(x.total_revenue);
        }).join('\n');
    }

    if (/(slow|least|worst).*(sell|seller|moving)|slow movers/.test(t)) {
      var prods = D.products.slice().sort(function (a, b) { return (a.total_units_sold || 0) - (b.total_units_sold || 0); });
      return 'Slowest movers by units sold:\n' +
        prods.slice(0, 8).map(function (x, i) {
          return (i + 1) + '. ' + x.name + ' (' + x.sku + ') — ' + (x.total_units_sold || 0) + ' units';
        }).join('\n');
    }

    if (/(forecast|predict|demand|next (week|days))/.test(t)) {
      var pf = findProduct(t);
      if (pf) {
        var dailyAvg = (pf.total_units_sold || 0) / 90;
        return 'Demand forecast for ' + pf.name + ' (' + pf.sku + ')\n' +
          '• Historical daily average (90d): ' + dailyAvg.toFixed(2) + ' units/day\n' +
          '• Expected next 7 days: ~' + Math.max(1, Math.round(dailyAvg * 7)) + ' units\n' +
          '• Current stock: ' + pf.current_stock + ' units (min ' + pf.min_stock_threshold + ')\n' +
          'Method: moving average.';
      }
      return 'Tell me which product or SKU to forecast, e.g. "forecast demand for SKU-0001".';
    }

    if (/(revenue|sales|sold|earn)/.test(t)) {
      var totalUnits = 0, totalRev = 0;
      D.products.forEach(function (x) { totalUnits += (x.total_units_sold || 0); totalRev += (x.total_revenue || 0); });
      return 'Sales summary (all time)\n' +
        '• Total units sold: ' + totalUnits.toLocaleString() + '\n' +
        '• Total revenue: ' + money(totalRev) + '\n' +
        '• Products with sales: ' + D.products.filter(function (x) { return x.total_units_sold > 0; }).length;
    }

    if (/(help|what can you|options)/.test(t)) {
      return 'I can answer questions like:\n' +
        '• "How many units of SKU-0002 are available?"\n' +
        '• "Which products are low in stock?"\n' +
        '• "Which products are out of stock?"\n' +
        '• "Show inventory summary"\n' +
        '• "What are the top sellers?"\n' +
        '• "Forecast demand for SKU-0001"\n' +
        '• "Show total revenue"';
    }

    return 'I can help with stock levels, low-stock items, top sellers, revenue, and demand forecasts.\n' +
      'Try: "How many units of SKU-0002 are available?"';
  }

  /* ---------- rendering ---------- */
  function clearThread(keepEmptyState) {
    var thread = $('chat-thread');
    thread.innerHTML = keepEmptyState
      ? '<div class="chat-empty" id="chat-empty"><h2>MenteE</h2><p>Ask about stock, sales, or forecasts — or request a chart.</p></div>'
      : '';
    updateHints();
  }

  function updateHints() {
    var hints = $('chat-hints');
    if (!hints) return;
    var thread = $('chat-thread');
    var hasMessages = !!(thread && thread.querySelector('.chat-row'));
    hints.style.display = hasMessages ? 'none' : '';
  }

  function addMessage(role, text, meta) {
    meta = meta || {};
    var empty = $('chat-empty');
    if (empty) empty.remove();
    var thread = $('chat-thread');
    var row = document.createElement('div');
    row.className = 'chat-row ' + role;
    var avatar = document.createElement('div');
    avatar.className = 'chat-avatar';
    avatar.textContent = role === 'user' ? 'You' : 'M';
    var bubble = document.createElement('div');
    bubble.className = 'chat-bubble' + (meta.error ? ' error' : '');
    var html = '<span class="who">' + (role === 'user' ? 'You' : 'MenteE') + '</span>';
    if (role === 'agent') {
      html += '<div class="md">' + mdToHtml(text) + '</div>';
    } else {
      html += esc(text);
    }
    if (meta.tools && meta.tools.length) {
      html += '<div class="chat-tools"><span class="chat-tools-label">used</span>' + meta.tools.map(function (t) {
        return '<span class="chat-tool">' + esc(t) + '</span>';
      }).join('') + '</div>';
    }
    bubble.innerHTML = html;
    row.appendChild(avatar);
    row.appendChild(bubble);
    thread.appendChild(row);
    if (meta.charts && meta.charts.length) renderChatCharts(bubble, meta.charts);
    updateHints();
    scrollBottom();
  }

  /* ---------- charts in chat ---------- */
  function chartAxisOptions() {
    var tick = '#6b6b6b';
    var grid = 'rgba(227,221,209,.6)';
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 300 },
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: tick, font: { size: 10 }, maxTicksLimit: 10, autoSkip: true }, grid: { color: grid } },
        y: { beginAtZero: true, ticks: { color: tick, font: { size: 10 } }, grid: { color: grid } },
      },
    };
  }

  function drawChatChart(canvas, spec) {
    var palette = ['#8b6f47', '#3a7d44', '#b8860b', '#c0392b', '#6b6b6b', '#a58b6f', '#7a9e7e', '#d0b28a'];
    var cfg;
    if (spec.chart_type === 'pie') {
      cfg = {
        type: 'pie',
        data: {
          labels: spec.labels,
          datasets: [{ data: spec.values, backgroundColor: palette, borderColor: '#ffffff', borderWidth: 1 }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'right', labels: { color: '#6b6b6b', boxWidth: 10, font: { size: 10 } } } },
        },
      };
    } else if (spec.chart_type === 'line') {
      cfg = {
        type: 'line',
        data: {
          labels: spec.labels,
          datasets: [{
            label: spec.value_label || 'Value',
            data: spec.values,
            borderColor: '#8b6f47',
            backgroundColor: 'rgba(139,111,71,.12)',
            fill: true, tension: .25, pointRadius: 2, borderWidth: 2,
          }],
        },
        options: chartAxisOptions(),
      };
    } else {
      cfg = {
        type: 'bar',
        data: {
          labels: spec.labels,
          datasets: [{
            label: spec.value_label || 'Value',
            data: spec.values,
            backgroundColor: 'rgba(139,111,71,.75)',
            borderColor: '#8b6f47',
            borderWidth: 1,
          }],
        },
        options: chartAxisOptions(),
      };
    }
    try {
      new Chart(canvas.getContext('2d'), cfg);
    } catch (e) { /* keep the message readable even if the chart fails */ }
  }

  function renderChatCharts(container, specs) {
    if (!specs || !specs.length) return;
    if (typeof Chart === 'undefined') return;
    specs.forEach(function (spec) {
      if (!spec || !spec.labels || !spec.values) return;
      var wrap = document.createElement('div');
      wrap.className = 'chat-chart';
      var box = document.createElement('div');
      box.className = 'chat-chart-box';
      var canvas = document.createElement('canvas');
      box.appendChild(canvas);
      wrap.appendChild(box);
      var toolsEl = container.querySelector('.chat-tools');
      if (toolsEl) container.insertBefore(wrap, toolsEl);
      else container.appendChild(wrap);
      drawChatChart(canvas, spec);
    });
  }

  function addTyping() {
    var thread = $('chat-thread');
    var row = document.createElement('div');
    row.className = 'chat-row agent';
    row.id = 'typing-row';
    row.innerHTML = '<div class="chat-avatar">M</div><div class="chat-bubble"><span class="who">MenteE</span><span class="chat-typing"><span></span><span></span><span></span></span></div>';
    thread.appendChild(row);
    scrollBottom();
  }
  function removeTyping() {
    var el = $('typing-row');
    if (el) el.remove();
  }
  function scrollBottom() {
    var sc = $('chat-scroll');
    if (sc) sc.scrollTop = sc.scrollHeight;
  }

  /* ---------- history side panel ---------- */
  function renderConvList() {
    var list = $('chat-conv-list');
    if (!list) return;
    var convs = loadConvs();
    var activeId = localStorage.getItem(LS_ACTIVE);
    if (!convs.length) {
      list.innerHTML = '<div class="chat-history-empty">No conversations yet.</div>';
      return;
    }
    list.innerHTML = convs.map(function (c) {
      var when = new Date(c.ts).toLocaleDateString();
      return '<div class="conv-item' + (c.id === activeId ? ' active' : '') + '" data-id="' + c.id + '" title="' + esc(c.title) + '">' +
        '<div class="t">' + esc(c.title) + '</div>' +
        '<div class="m">' + c.messages.length + ' messages · ' + when + '</div>' +
        '<button class="conv-del" data-del="' + c.id + '" title="Delete conversation">×</button>' +
        '</div>';
    }).join('');

    list.querySelectorAll('.conv-item').forEach(function (item) {
      item.addEventListener('click', function (e) {
        if (e.target.closest('.conv-del')) return;
        switchConv(item.getAttribute('data-id'));
      });
    });
    list.querySelectorAll('.conv-del').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        confirmDialog('Delete conversation', 'This conversation and all its messages will be permanently removed.', function () {
          deleteConv(btn.getAttribute('data-del'));
        });
      });
    });
  }

  function confirmDialog(title, message, onConfirm) {
    var existing = $('chat-confirm');
    if (existing) existing.remove();

    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.id = 'chat-confirm';
    overlay.innerHTML =
      '<div class="modal confirm-modal">' +
        '<div class="modal-head"><h2>' + esc(title) + '</h2>' +
        '<button class="modal-close" title="Cancel" data-act="cancel">×</button></div>' +
        '<p class="confirm-text">' + esc(message) + '</p>' +
        '<div class="confirm-actions">' +
          '<button class="btn-ghost" data-act="cancel">Cancel</button>' +
          '<button class="btn-danger" data-act="confirm">Delete</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(overlay);

    function close() {
      overlay.remove();
      document.removeEventListener('keydown', onKey);
    }
    function onKey(e) {
      if (e.key === 'Escape') close();
    }

    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) { close(); return; }
      var act = e.target.getAttribute ? e.target.getAttribute('data-act') : null;
      if (!act) return;
      if (act === 'confirm') {
        close();
        onConfirm();
      } else {
        close();
      }
    });
    document.addEventListener('keydown', onKey);
  }

  function deleteConv(id) {
    var convs = loadConvs();
    var removed = null;
    convs = convs.filter(function (c) {
      if (c.id === id) { removed = c; return false; }
      return true;
    });
    saveConvs(convs);
    if (localStorage.getItem(LS_ACTIVE) === id) {
      if (convs.length) {
        switchConv(convs[0].id);
        return;
      }
      localStorage.removeItem(LS_ACTIVE);
      clearThread(true);
    }
    renderConvList();
  }

  function newChat() {
    var convs = loadConvs();
    var conv = createConv(convs);
    clearThread(true);
    renderConvList();
    var input = $('chat-input');
    if (input) input.focus();
  }

  function switchConv(id) {
    localStorage.setItem(LS_ACTIVE, id);
    var convs = loadConvs();
    var conv = null;
    for (var i = 0; i < convs.length; i++) if (convs[i].id === id) conv = convs[i];
    clearThread(false);
    if (conv && conv.messages.length) {
      conv.messages.forEach(function (m) { addMessage(m.role, m.text, { tools: m.tools, charts: m.charts }); });
    } else {
      clearThread(true);
    }
    renderConvList();
  }

  /* ---------- agent call (live mode) ---------- */
  function callAgent(q) {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 120000);
    return fetch(window.appApiBase() + '/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: q }),
      signal: controller.signal
    }).finally(function () { clearTimeout(timer); }).then(function (r) {
      if (!r.ok) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          throw new Error(j.detail || ('HTTP ' + r.status));
        });
      }
      return r.json();
    });
  }

  /* ---------- send flow ---------- */
  function send(text) {
    var input = $('chat-input');
    var q = (text !== undefined ? text : input.value).trim();
    if (!q || busy) return;
    input.value = '';
    autoResize();
    addMessage('user', q);

    var conv = getActiveConv();
    conv.messages.push({ role: 'user', text: q, ts: Date.now() });
    if (conv.title === 'New conversation') {
      conv.title = q.length > 42 ? q.slice(0, 42) + '…' : q;
    }
    persist(conv);
    renderConvList();

    busy = true;
    addTyping();

    if (window.APP_MODE === 'live') {
      callAgent(q).then(function (res) {
        removeTyping();
        var a = res.answer || '(empty response from the model)';
        addMessage('agent', a, { tools: res.tools, charts: res.charts });
        conv = getActiveConv();
        conv.messages.push({ role: 'agent', text: a, tools: res.tools || [], charts: res.charts || [], ts: Date.now() });
        persist(conv);
        renderConvList();
      }).catch(function (err) {
        removeTyping();
        addMessage('agent', 'Agent error: ' + err.message + '\n\nNo fallback is used — check the server and the LLM configuration.', { error: true });
      }).finally(function () {
        busy = false;
      });
      return;
    }

    // snapshot mode — local intent engine over the bundled data
    setTimeout(function () {
      removeTyping();
      var a = answer(q);
      addMessage('agent', a);
      conv = getActiveConv();
      conv.messages.push({ role: 'agent', text: a, ts: Date.now() });
      persist(conv);
      busy = false;
    }, 350);
  }

  function autoResize() {
    var input = $('chat-input');
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 160) + 'px';
  }

  /* ---------- view template ---------- */
  var HINTS = [
    'Show inventory summary',
    'Which products are low in stock?',
    'What should I reorder first?',
    'Make a bar chart of the top sellers',
    'Chart daily revenue for the last 30 days',
    'Forecast demand for SKU-0001'
  ];

  function template() {
    return `
      <div class="chat-layout">
        <div class="chat-history">
          <div class="chat-history-head">
            <div class="chat-history-title">Conversations</div>
            <button class="chat-newbtn" id="chat-new">+ New chat</button>
          </div>
          <div class="chat-history-list" id="chat-conv-list"></div>
        </div>
        <div class="chat-main">
          <div class="chat-scroll" id="chat-scroll">
            <div class="chat-thread" id="chat-thread">
              <div class="chat-empty" id="chat-empty">
                <h2>MenteE</h2>
                <p>Ask about stock, sales, or forecasts — or request a chart.</p>
              </div>
            </div>
          </div>
          <div class="chat-composer">
            <div class="chat-hints" id="chat-hints">
              ${HINTS.map(h => `<button class="chat-hint" data-q="${esc(h)}">${esc(h)}</button>`).join('')}
            </div>
            <div class="chat-composer-inner">
              <textarea id="chat-input" rows="1" placeholder="Ask a question..."></textarea>
              <button class="chat-send" id="chat-send" title="Send">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
              </button>
            </div>
          </div>
        </div>
      </div>`;
  }

  /* ---------- mount (called by app.js when chat view opens) ---------- */
  function mount() {
    D = window.PRODUCTS_DATA || null;
    var input = $('chat-input');
    var sendBtn = $('chat-send');
    var newBtn = $('chat-new');
    if (!input || !sendBtn) return;

    // restore active conversation
    var conv = getActiveConv();
    if (conv.messages.length) {
      clearThread(false);
      conv.messages.forEach(function (m) { addMessage(m.role, m.text, { tools: m.tools, charts: m.charts }); });
    } else if (window.APP_MODE !== 'live') {
      addMessage('agent', 'Backend offline — running in snapshot mode.\nStart the API (uvicorn src.api.main:app) to chat with the real LangGraph agent over live data.');
    }
    renderConvList();

    sendBtn.addEventListener('click', function () { send(); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });
    input.addEventListener('input', autoResize);
    newBtn.addEventListener('click', newChat);

    document.querySelectorAll('.chat-hint').forEach(function (b) {
      b.addEventListener('click', function () { send(b.getAttribute('data-q')); });
    });

    if (!D && window.APP_MODE !== 'live') addMessage('agent', 'Data not loaded. Run `python scripts/init_db.py` then `python scripts/generate_products_html.py`, or start the API.');
    input.focus();
  }

  window.ChatUI = { mount: mount, template: template, send: send };
})();