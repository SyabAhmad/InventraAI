/* InventraAI — Chat view (ChatGPT-style) with persistent conversation history.
   Local intent engine over real dashboard data. The FastAPI backend will swap
   `answer()` for the LLM agent; the UI stays the same. */
(function () {
  'use strict';

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function money(n) { return '$' + Number(n).toFixed(2); }

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
      ? '<div class="chat-empty" id="chat-empty"><h2>Inventory Assistant</h2><p>Ask about stock levels, low-stock items, sales, or demand forecasts.</p></div>'
      : '';
  }

  function addMessage(role, text) {
    var empty = $('chat-empty');
    if (empty) empty.remove();
    var thread = $('chat-thread');
    var row = document.createElement('div');
    row.className = 'chat-row ' + role;
    var avatar = document.createElement('div');
    avatar.className = 'chat-avatar';
    avatar.textContent = role === 'user' ? 'You' : 'AI';
    var bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    bubble.innerHTML = '<span class="who">' + (role === 'user' ? 'You' : 'Agent') + '</span>' + esc(text);
    row.appendChild(avatar);
    row.appendChild(bubble);
    thread.appendChild(row);
    scrollBottom();
  }

  function addTyping() {
    var thread = $('chat-thread');
    var row = document.createElement('div');
    row.className = 'chat-row agent';
    row.id = 'typing-row';
    row.innerHTML = '<div class="chat-avatar">AI</div><div class="chat-bubble"><span class="who">Agent</span><span class="chat-typing"><span></span><span></span><span></span></span></div>';
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
        deleteConv(btn.getAttribute('data-del'));
      });
    });
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
      conv.messages.forEach(function (m) { addMessage(m.role, m.text); });
    } else {
      clearThread(true);
    }
    renderConvList();
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
    'Which products are out of stock?',
    'What are the top sellers?',
    'Forecast demand for SKU-0001',
    'How many units of SKU-0002 are available?'
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
                <h2>Inventory Assistant</h2>
                <p>Ask about stock levels, low-stock items, sales, or demand forecasts.</p>
              </div>
            </div>
          </div>
          <div class="chat-composer">
            <div class="chat-hints">
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
      conv.messages.forEach(function (m) { addMessage(m.role, m.text); });
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

    if (!D) addMessage('agent', 'Data not loaded. Run `python scripts/generate_products_html.py` first.');
    input.focus();
  }

  window.ChatUI = { mount: mount, template: template, send: send };
})();