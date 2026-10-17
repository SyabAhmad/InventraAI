/* InventraAI — Chat agent (local intent engine over real dashboard data).
   Phase 4 will replace `answer()` with the LLM agent; the UI stays the same. */
(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };
  var D = window.PRODUCTS_DATA || null;

  /* ---------- helpers ---------- */
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function money(n) { return '$' + Number(n).toFixed(2); }
  function findProduct(q) {
    if (!D) return null;
    var t = q.toLowerCase();
    var m = t.match(/sku[- ]?(\d{3,4})/);
    if (m) {
      var sku = 'SKU-' + ('0000' + m[1]).slice(-4);
      for (var i = 0; i < D.products.length; i++) {
        if (D.products[i].sku.toLowerCase() === sku) return D.products[i];
      }
    }
    // name match (best contains)
    var best = null;
    for (var j = 0; j < D.products.length; j++) {
      var name = D.products[j].name.toLowerCase();
      if (t.indexOf(name) !== -1) { best = D.products[j]; break; }
    }
    return best;
  }
  function statusOf(p) {
    if (p.current_stock === 0) return 'out of stock';
    if (p.current_stock < p.min_stock_threshold) return 'low stock';
    return 'healthy';
  }

  /* ---------- intents ---------- */
  function answer(q) {
    if (!D) return 'Data not loaded. Regenerate the dashboard first.';
    var t = q.toLowerCase().trim();

    // stock of a product
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
      if (/(low|below)/.test(t) && /(stock|items)/.test(t)) {
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

    // summary
    if (/(summary|overview|how is inventory|total)/.test(t)) {
      var s = D.summary;
      return 'Inventory summary\n' +
        '• Products: ' + s.total_products + '\n' +
        '• Total stock units: ' + s.total_stock_units.toLocaleString() + '\n' +
        '• Low stock: ' + s.low_stock_count + '\n' +
        '• Out of stock: ' + s.out_of_stock_count + '\n' +
        '• Inventory value: ' + money(s.inventory_value_at_price);
    }

    // top sellers
    if (/(top|best|fast).*(sell|seller|moving)|top sellers/.test(t)) {
      if (!D.top_sellers.length) return 'No sales data yet.';
      return 'Top sellers by units sold:\n' +
        D.top_sellers.slice(0, 8).map(function (x, i) {
          return (i + 1) + '. ' + x.name + ' (' + x.category + ') — ' + x.total_units + ' units, ' + money(x.total_revenue);
        }).join('\n');
    }

    // slow movers
    if (/(slow|least|worst).*(sell|seller|moving)|slow movers/.test(t)) {
      var prods = D.products.slice().sort(function (a, b) { return (a.total_units_sold || 0) - (b.total_units_sold || 0); });
      return 'Slowest movers by units sold:\n' +
        prods.slice(0, 8).map(function (x, i) {
          return (i + 1) + '. ' + x.name + ' (' + x.sku + ') — ' + (x.total_units_sold || 0) + ' units';
        }).join('\n');
    }

    // forecast
    if (/(forecast|predict|demand|next (week|days))/.test(t)) {
      var pf = findProduct(t);
      if (pf) {
        var sold = pf.total_units_sold || 0;
        var dailyAvg = (sold / 90).toFixed(2);
        return 'Demand forecast for ' + pf.name + ' (' + pf.sku + ')\n' +
          '• Historical daily average (90d): ' + dailyAvg + ' units/day\n' +
          '• Expected next 7 days: ~' + Math.round(dailyAvg * 7) + ' units\n' +
          '• Current stock: ' + pf.current_stock + ' units (min ' + pf.min_stock_threshold + ')\n' +
          'Method: moving average. Full method comparison is on the Sales Summary page.';
      }
      return 'Tell me which product or SKU to forecast, e.g. "forecast demand for SKU-0001".';
    }

    // sales / revenue
    if (/(revenue|sales|sold|earn)/.test(t)) {
      var totalUnits = 0, totalRev = 0;
      D.products.forEach(function (x) { totalUnits += (x.total_units_sold || 0); totalRev += (x.total_revenue || 0); });
      return 'Sales summary (all time)\n' +
        '• Total units sold: ' + totalUnits.toLocaleString() + '\n' +
        '• Total revenue: ' + money(totalRev) + '\n' +
        '• Products with sales: ' + D.products.filter(function (x) { return x.total_units_sold > 0; }).length + '\n' +
        'Category revenue leaders are on the Sales Summary page.';
    }

    // help
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
      'Try: "How many units of SKU-0002 are available?" or tap a suggestion below.';
  }

  /* ---------- rendering ---------- */
  function addMessage(role, text) {
    var thread = $('chat-thread');
    var empty = $('chat-empty');
    if (empty) empty.remove();

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
    return bubble;
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
    sc.scrollTop = sc.scrollHeight;
  }

  /* ---------- send flow ---------- */
  var busy = false;
  function send(text) {
    var input = $('chat-input');
    var q = (text !== undefined ? text : input.value).trim();
    if (!q || busy) return;
    input.value = '';
    autoResize();
    addMessage('user', q);
    busy = true;
    addTyping();
    setTimeout(function () {
      removeTyping();
      var a = answer(q);
      addMessage('agent', a);
      busy = false;
    }, 350);
  }

  function autoResize() {
    var input = $('chat-input');
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 160) + 'px';
  }

  /* ---------- init ---------- */
  document.addEventListener('DOMContentLoaded', function () {
    if (!D) {
      addMessage('agent', 'Data not loaded. Run `python scripts/generate_products_html.py` first.');
      return;
    }
    var badge = $('model-badge');
    if (badge && D.config && D.config.LLM_MODEL) badge.textContent = D.config.LLM_MODEL;

    var input = $('chat-input');
    var sendBtn = $('chat-send');

    sendBtn.addEventListener('click', function () { send(); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        send();
      }
    });
    input.addEventListener('input', autoResize);

    document.querySelectorAll('.chat-hint').forEach(function (b) {
      b.addEventListener('click', function () { send(b.getAttribute('data-q')); });
    });
  });
})();