/* InventraAI dashboard — view router + components.
   Live mode: data and charts come from the FastAPI backend (uvicorn src.api.main:app).
   Snapshot mode: falls back to the bundled data.js file when the backend is offline. */
(function () {
  'use strict';

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function statusOf(p) {
    if (p.current_stock === 0) return 'out';
    if (p.current_stock < p.min_stock_threshold) return 'low';
    return 'ok';
  }
  function statusLabel(s) { return s === 'out' ? 'Out' : s === 'low' ? 'Low' : 'OK'; }

  const TITLES = {
    overview: 'Dashboard', products: 'Products', lowstock: 'Low Stock',
    outofstock: 'Out of Stock', topsellers: 'Top Sellers',
    sales: 'Sales Summary', reorder: 'Reorder Advice', settings: 'Settings', chat: 'Chat',
  };

  /* ================= API access ================= */
  function apiBase() {
    if (window.INVENTRAAI_API_BASE) return window.INVENTRAAI_API_BASE;
    if (location.protocol === 'http:' || location.protocol === 'https:') return '';
    return 'http://127.0.0.1:8000'; // opened as a local file: talk to the default backend
  }
  window.appApiBase = apiBase;

  function fetchJson(path, timeoutMs) {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, timeoutMs || 4000);
    return fetch(apiBase() + path, { signal: controller.signal })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .finally(function () { clearTimeout(timer); });
  }
  window.appFetchJson = fetchJson;

  async function loadData() {
    try {
      var payload = await fetchJson('/api/dashboard', 4000);
      if (payload && payload.products && payload.products.length) {
        window.APP_MODE = 'live';
        return payload;
      }
    } catch (e) { /* backend not reachable — use the bundled snapshot */ }
    window.APP_MODE = 'snapshot';
    return window.PRODUCTS_DATA || null;
  }

  /* ================= charts ================= */
  function lineChart(canvasId, labels, datasets, opts) {
    var canvas = $(canvasId);
    if (!canvas || typeof Chart === 'undefined') return null;
    opts = opts || {};
    var tickColor = '#6b6b6b';
    var gridColor = 'rgba(227,221,209,.6)';
    var scales = {
      x: { ticks: { color: tickColor, maxTicksLimit: 12, font: { size: 10 } }, grid: { color: gridColor } },
      y: { beginAtZero: true, ticks: { color: tickColor, font: { size: 10 } }, grid: { color: gridColor } },
    };
    if (opts.unitsAxis) {
      scales.units = {
        position: 'right', beginAtZero: true,
        grid: { drawOnChartArea: false },
        ticks: { color: tickColor, font: { size: 10 } },
      };
    }
    return new Chart(canvas.getContext('2d'), {
      type: 'line',
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 350 },
        interaction: { mode: 'index', intersect: false },
        plugins: { legend: { labels: { color: tickColor, boxWidth: 12, font: { size: 11 } } } },
        scales: scales,
      },
    });
  }

  function card(label, value, hint, color) {
    return `<div class="card"><div class="label">${label}</div><div class="value" ${color ? `style="color:${color}"` : ''}>${value}</div><div class="hint">${hint}</div></div>`;
  }

  function renderOverview(D) {
    const s = D.summary;
    let banner = '';
    if (s.out_of_stock_count > 0) {
      banner = `<div class="attention-banner"><span class="icon">⚠</span><div><strong>Action required:</strong> ${s.out_of_stock_count} product(s) are out of stock and ${s.low_stock_count} are running low. Review the Low Stock and Out of Stock pages.</div></div>`;
    } else if (s.low_stock_count > 0) {
      banner = `<div class="attention-banner warn"><span class="icon">⚠</span><div><strong>Attention:</strong> ${s.low_stock_count} product(s) are below their minimum stock level.</div></div>`;
    }
    $('content').innerHTML = `
      ${banner}
      <div class="cards">
        ${card('Total Products', s.total_products.toLocaleString(), 'In catalogue')}
        ${card('Total Stock Units', s.total_stock_units.toLocaleString(), 'Across all products')}
        ${card('Low Stock', s.low_stock_count.toLocaleString(), 'Below minimum threshold', 'var(--yellow)')}
        ${card('Out of Stock', s.out_of_stock_count.toLocaleString(), 'Zero units available', 'var(--red)')}
        ${card('Inventory Value', '$' + s.inventory_value_at_price.toLocaleString(), 'At selling price')}
      </div>
      <div class="section">
        <h1 style="color:var(--red);font-size:18px;font-weight:700;">⚠ Needs Attention</h1>
        <button id="attn-btn" onclick="var b=document.getElementById('low-alerts'); var h=b.style.display==='none'; b.style.display=h?'':'none'; this.textContent=h?'Hide List':'Show List';" style="margin-bottom:8px;background:var(--red);color:#fff;border:none;padding:6px 10px;border-radius:2px;font-size:12px;font-weight:600;cursor:pointer;">Show / Hide List</button>
        <div class="toolbar" style="margin-bottom:8px">
          <input type="text" id="attn-search" placeholder="Search attention items by name, SKU, or category..." />
          <select id="attn-filter">
            <option value="">All attention items</option>
            <option value="out">Out of stock only</option>
            <option value="low">Low stock only</option>
          </select>
        </div>
        <div class="alert-list collapsible-body" id="low-alerts"></div>
      </div>
      <div class="section">
        <h2>Top Sellers</h2>
        <div class="top-list" id="top-sellers"></div>
      </div>`;
    renderAlerts(D.low_stock, D.out_of_stock);
    renderTopSellers(D.top_sellers);
    const btn = $('attn-btn');
    if (btn) {
      btn.onclick = () => {
        const body = $('low-alerts');
        const hidden = body.style.display === 'none';
        body.style.display = hidden ? '' : 'none';
        btn.textContent = hidden ? 'Hide List' : 'Show List';
      };
    }
  }

  let _attnItems = [];
  function renderAlerts(lowStock, outOfStock) {
    _attnItems = [...outOfStock, ...lowStock];
    const input = $('attn-search');
    const filterSel = $('attn-filter');
    const apply = () => {
      const el = $('low-alerts');
      const q = (input ? input.value : '').toLowerCase();
      const f = filterSel ? filterSel.value : '';
      const items = _attnItems.filter(p => {
        if (f === 'out' && p.current_stock !== 0) return false;
        if (f === 'low' && !(p.current_stock > 0 && p.current_stock < p.min_stock_threshold)) return false;
        if (q && !(p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q) || p.category.toLowerCase().includes(q))) return false;
        return true;
      }).slice(0, 20);
      if (!items.length) { el.innerHTML = '<div class="empty">No matching items.</div>'; return; }
      el.innerHTML = items.map(p => {
        const isOut = p.current_stock === 0;
        return `<div class="alert-item${isOut ? '' : ' low'}">
          <div class="info">
            <strong>${esc(p.name)}</strong> <span style="color:var(--muted)">(${esc(p.sku)})</span>
            <div class="meta">${esc(p.category)} · min threshold ${p.min_stock_threshold} · $${p.price.toFixed(2)}</div>
          </div>
          <div class="qty ${isOut ? 'out' : 'low'}">${p.current_stock} units</div>
        </div>`;
      }).join('');
    };
    if (input) {
      input.addEventListener('input', apply);
    }
    if (filterSel) {
      filterSel.addEventListener('change', apply);
    }
    apply();
  }

  function renderTopSellers(list) {
    const el = $('top-sellers');
    el.innerHTML = list.slice(0, 8).map((t, i) =>
      `<div class="top-item"><div class="name">#${i + 1} ${esc(t.name)}</div>
       <div class="meta">${esc(t.category)} · ${t.total_units} units · $${Number(t.total_revenue).toFixed(2)}</div></div>`).join('');
  }

  function renderProducts(D) {
    const cats = [...new Set(D.products.map(p => p.category))].sort();
    $('content').innerHTML = `
      <div class="section">
        <div class="toolbar">
          <input type="text" id="search" placeholder="Search by name, SKU, or category..." />
          <select id="cat-filter"><option value="">All categories</option>${cats.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join('')}</select>
          <select id="status-filter">
            <option value="">All statuses</option><option value="ok">Healthy</option><option value="low">Low stock</option><option value="out">Out of stock</option>
          </select>
          <select id="sort">
            <option value="name">Sort: Name</option><option value="stock-asc">Sort: Stock (low first)</option>
            <option value="stock-desc">Sort: Stock (high first)</option><option value="price-desc">Sort: Price (high first)</option>
            <option value="sold-desc">Sort: Units sold (high first)</option>
          </select>
        </div>
        <table>
          <thead><tr><th>SKU</th><th>Name</th><th>Category</th><th class="num">Price</th><th class="num">Stock</th><th class="num">Min</th><th>Status</th><th class="num">Units Sold</th><th class="num">Revenue</th></tr></thead>
          <tbody id="tbody"></tbody>
        </table>
        <div class="empty" id="empty-msg" style="display:none">No products match your filters.</div>
        <div class="sub" style="margin-top:8px">Click a row for stock details and the demand forecast.</div>
      </div>`;
    const rerender = () => renderTable(D.products);
    ['search', 'cat-filter', 'status-filter', 'sort'].forEach(id => {
      $(id).addEventListener('input', rerender);
      $(id).addEventListener('change', rerender);
    });
    $('tbody').addEventListener('click', (e) => {
      const tr = e.target.closest('tr[data-sku]');
      if (tr) openProductDetail(tr.getAttribute('data-sku'));
    });
    renderTable(D.products);
  }

  function renderTable(products) {
    const q = $('search').value.toLowerCase();
    const cat = $('cat-filter').value;
    const st = $('status-filter').value;
    const sort = $('sort').value;
    let rows = products.filter(p => {
      if (cat && p.category !== cat) return false;
      if (st && statusOf(p) !== st) return false;
      if (q && !(p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q) || p.category.toLowerCase().includes(q))) return false;
      return true;
    });
    rows.sort((a, b) => {
      switch (sort) {
        case 'stock-asc': return a.current_stock - b.current_stock;
        case 'stock-desc': return b.current_stock - a.current_stock;
        case 'price-desc': return b.price - a.price;
        case 'sold-desc': return (b.total_units_sold || 0) - (a.total_units_sold || 0);
        default: return a.name.localeCompare(b.name);
      }
    });
    $('tbody').innerHTML = rows.map(p => {
      const s = statusOf(p);
      return `<tr class="clickable" data-sku="${esc(p.sku)}">
        <td>${esc(p.sku)}</td><td>${esc(p.name)}</td><td>${esc(p.category)}</td>
        <td class="num">$${p.price.toFixed(2)}</td><td class="num">${p.current_stock}</td><td class="num">${p.min_stock_threshold}</td>
        <td><span class="status ${s}">${statusLabel(s)}</span></td>
        <td class="num">${p.total_units_sold || 0}</td><td class="num">$${(p.total_revenue || 0).toFixed(2)}</td>
      </tr>`;
    }).join('');
    $('empty-msg').style.display = rows.length ? 'none' : 'block';
  }

  /* ================= product detail modal ================= */
  function closeModal() {
    const m = $('product-modal');
    if (m) m.remove();
  }

  function openProductDetail(sku) {
    const D = window.PRODUCTS_DATA;
    let p = null;
    for (let i = 0; i < D.products.length; i++) {
      if (D.products[i].sku === sku) { p = D.products[i]; break; }
    }
    if (!p) return;

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.id = 'product-modal';
    overlay.innerHTML = `
      <div class="modal">
        <div class="modal-head">
          <div>
            <h2>${esc(p.name)}</h2>
            <div class="sub">${esc(p.sku)} · ${esc(p.category)}</div>
          </div>
          <button class="modal-close" title="Close">×</button>
        </div>
        <div class="kv">
          <div><div class="k">Current stock</div><div class="v">${p.current_stock} units</div></div>
          <div><div class="k">Min threshold</div><div class="v">${p.min_stock_threshold}</div></div>
          <div><div class="k">Price</div><div class="v">$${Number(p.price).toFixed(2)}</div></div>
          <div><div class="k">Units sold (all time)</div><div class="v">${p.total_units_sold || 0}</div></div>
        </div>
        <div class="section" style="margin-top:16px;margin-bottom:0">
          <h3 class="modal-h3">Demand — last 90 days + forecast</h3>
          <div class="chart-box"><canvas id="detail-chart"></canvas></div>
          <div class="sub" id="detail-note" style="margin-top:6px"></div>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    overlay.addEventListener('click', (e) => { if (e.target === overlay) closeModal(); });
    overlay.querySelector('.modal-close').addEventListener('click', closeModal);
    document.addEventListener('keydown', function onEsc(e) {
      if (e.key === 'Escape') { closeModal(); document.removeEventListener('keydown', onEsc); }
    });

    const note = $('detail-note');
    if (window.APP_MODE === 'live') {
      note.textContent = 'Loading forecast…';
      fetchJson('/api/forecast/' + encodeURIComponent(sku), 15000).then((f) => {
        if (!$('detail-chart')) return;
        const labels = f.history.map(h => h.date.slice(5)).concat(f.forecast.map(x => x.date.slice(5)));
        const hist = f.history.map(h => h.units);
        const fc = f.forecast.map(x => x.predicted_qty);
        const histSeries = hist.concat(fc.map(() => null));
        const fcSeries = hist.map(() => null).concat(fc);
        fcSeries[hist.length - 1] = hist[hist.length - 1]; // connect the lines
        lineChart('detail-chart', labels, [
          { label: 'Actual units/day', data: histSeries, borderColor: '#8b6f47', backgroundColor: 'rgba(139,111,71,.12)', fill: true, tension: .25, pointRadius: 0, borderWidth: 2 },
          { label: 'Forecast', data: fcSeries, borderColor: '#3a7d44', borderDash: [6, 4], tension: .25, pointRadius: 0, borderWidth: 2 },
        ]);
        const m = f.metrics || {};
        note.textContent = 'Method: ' + f.method + ' · next ' + f.forecast.length + ' days ≈ ' + f.forecast_total +
          ' units · validation MAE ' + (m.mae !== undefined ? m.mae : '—') +
          ', MAPE ' + (m.mape !== undefined ? m.mape + '%' : '—');
      }).catch((err) => {
        const n = $('detail-note');
        if (n) n.textContent = 'Forecast unavailable: ' + err.message;
      });
    } else {
      note.textContent = 'Snapshot mode — start the FastAPI backend for the live forecast chart.';
      const c = $('detail-chart');
      if (c) c.style.display = 'none';
    }
  }

  function renderLowStock(D) {
    const items = D.low_stock;
    $('content').innerHTML = `
      <div class="section"><h2>Low-Stock Products (${items.length})</h2>
        <div class="alert-list">${items.length ? items.map(p =>
          `<div class="alert-item low clickable" data-sku="${esc(p.sku)}"><strong>${esc(p.name)}</strong> (${esc(p.sku)}) — ${p.current_stock} units left (min ${p.min_stock_threshold}) · ${esc(p.category)} · $${p.price.toFixed(2)}</div>`).join('') : '<div class="empty">No low-stock items 🎉</div>'}
        </div>
      </div>`;
    $('content').querySelectorAll('[data-sku]').forEach(el => {
      el.addEventListener('click', () => openProductDetail(el.getAttribute('data-sku')));
    });
  }

  function renderOutOfStock(D) {
    const items = D.out_of_stock;
    $('content').innerHTML = `
      <div class="section"><h2>Out-of-Stock Products (${items.length})</h2>
        <div class="alert-list">${items.length ? items.map(p =>
          `<div class="alert-item clickable" data-sku="${esc(p.sku)}"><strong>${esc(p.name)}</strong> (${esc(p.sku)}) — 0 units · ${esc(p.category)} · $${p.price.toFixed(2)}</div>`).join('') : '<div class="empty">No out-of-stock items 🎉</div>'}
        </div>
      </div>`;
    $('content').querySelectorAll('[data-sku]').forEach(el => {
      el.addEventListener('click', () => openProductDetail(el.getAttribute('data-sku')));
    });
  }

  function renderTopSellers(D) {
    $('content').innerHTML = `
      <div class="section"><h2>Top Sellers by Units Sold</h2>
        <div class="top-list">${D.top_sellers.map((t, i) =>
          `<div class="top-item"><div class="name">#${i + 1} ${esc(t.name)}</div><div class="meta">${esc(t.category)} · ${t.total_units} units · $${Number(t.total_revenue).toFixed(2)}</div></div>`).join('')}
        </div>
      </div>`;
  }

  function renderSales(D) {
    const totalUnits = D.products.reduce((a, p) => a + (p.total_units_sold || 0), 0);
    const totalRev = D.products.reduce((a, p) => a + (p.total_revenue || 0), 0);
    const cats = {};
    D.products.forEach(p => { cats[p.category] = (cats[p.category] || 0) + (p.total_revenue || 0); });
    $('content').innerHTML = `
      <div class="cards">
        ${card('Total Units Sold', totalUnits.toLocaleString(), 'All time')}
        ${card('Total Revenue', '$' + totalRev.toFixed(2), 'All time')}
        ${card('Avg per Product', '$' + (totalRev / D.products.length).toFixed(2), 'Revenue per product')}
        ${card('Products Sold', D.products.filter(p => p.total_units_sold > 0).length, 'With at least one sale')}
      </div>
      <div class="section"><h2>Revenue — last 30 days</h2>
        <div class="card chart-card">
          <div class="chart-box"><canvas id="sales-chart"></canvas></div>
          <div class="sub" id="sales-chart-note"></div>
        </div>
      </div>
      <div class="section"><h2>Revenue by Category</h2>
        <div class="top-list">${Object.entries(cats).sort((a, b) => b[1] - a[1]).map(([c, v]) =>
          `<div class="top-item"><div class="name">${esc(c)}</div><div class="meta">$${v.toFixed(2)}</div></div>`).join('')}
        </div>
      </div>`;

    const series = D.sales_daily_30d || [];
    const note = $('sales-chart-note');
    if (typeof Chart === 'undefined') {
      if (note) note.textContent = 'Chart library not loaded.';
    } else if (!series.length) {
      if (note) note.textContent = 'No daily sales data available.';
    } else {
      lineChart('sales-chart', series.map(p => p.date.slice(5)), [
        { label: 'Revenue ($)', data: series.map(p => p.revenue), borderColor: '#8b6f47', backgroundColor: 'rgba(139,111,71,.12)', fill: true, tension: .25, pointRadius: 0, borderWidth: 2 },
        { label: 'Units', data: series.map(p => p.units), borderColor: '#3a7d44', tension: .25, pointRadius: 0, borderWidth: 2, yAxisID: 'units' },
      ], { unitsAxis: true });
      if (note) note.textContent = series.length + ' days · revenue and units per day.';
    }
  }

  function renderReorder() {
    $('content').innerHTML = '<div class="section"><h2>Reorder Recommendations</h2><div id="reorder-body"></div></div>';
    const body = $('reorder-body');
    if (window.APP_MODE !== 'live') {
      body.innerHTML = '<div class="empty">Snapshot mode — start the FastAPI backend to compute live reorder recommendations.</div>';
      return;
    }
    body.innerHTML = '<div class="empty">Computing recommendations…</div>';
    fetchJson('/api/reorder?limit=50', 30000).then((res) => {
      const items = res.items || [];
      if (!items.length) {
        body.innerHTML = '<div class="empty">No products need reordering right now.</div>';
        return;
      }
      body.innerHTML = `
        <div class="sub" style="margin-bottom:8px">${items.length} product(s) recommended for reorder · sorted by urgency · computed from stock, demand and lead time</div>
        <table>
          <thead><tr><th>SKU</th><th>Name</th><th>Urgency</th><th class="num">Stock</th><th class="num">Reorder point</th><th class="num">Suggested qty</th><th>Reason (hover)</th></tr></thead>
          <tbody>${items.map(r => `
            <tr class="clickable" data-sku="${esc(r.sku)}">
              <td>${esc(r.sku)}</td><td>${esc(r.name)}</td>
              <td><span class="urgency ${r.urgency.toLowerCase()}">${r.urgency}</span></td>
              <td class="num">${r.current_stock}</td>
              <td class="num">${r.reorder_point}</td>
              <td class="num"><strong>${r.recommended_reorder_qty}</strong></td>
              <td class="reason-cell sub" title="${esc(r.reason)}">${esc(r.reason)}</td>
            </tr>`).join('')}
          </tbody>
        </table>`;
      body.querySelectorAll('tr[data-sku]').forEach(tr => {
        tr.addEventListener('click', () => openProductDetail(tr.getAttribute('data-sku')));
      });
    }).catch((err) => {
      body.innerHTML = '<div class="empty">Could not load recommendations: ' + esc(err.message) + '</div>';
    });
  }

  function renderSettings(D) {
    $('content').innerHTML = `
      <div class="section"><h2>Configuration (from .env)</h2>
        <div class="kv">
          <div><div class="k">Data source</div><div class="v">${window.APP_MODE === 'live' ? 'Live API (SQLite via FastAPI)' : 'Offline snapshot (data.js)'}</div></div>
          <div><div class="k">LLM Provider</div><div class="v">${esc(D.config.LLM_PROVIDER || '—')}</div></div>
          <div><div class="k">LLM Model</div><div class="v">${esc(D.config.LLM_MODEL || '—')}</div></div>
          <div><div class="k">LLM Base URL</div><div class="v">${esc(D.config.LLM_BASE_URL || '—')}</div></div>
          <div><div class="k">Database</div><div class="v">${esc(D.config.DATABASE_PATH || '—')}</div></div>
          <div><div class="k">Default Min Stock</div><div class="v">${D.config.DEFAULT_MIN_STOCK || '—'}</div></div>
          <div><div class="k">Forecast Horizon</div><div class="v">${D.config.FORECAST_HORIZON_DAYS ? D.config.FORECAST_HORIZON_DAYS + ' days' : '—'}</div></div>
        </div>
        <p class="empty" style="margin-top:12px">Edit <code>.env</code> to change these values — the live dashboard picks them up on the next load.</p>
      </div>`;
  }

  function renderChat() {
    $('content').classList.add('chat-mode');
    $('content').innerHTML = window.ChatUI ? window.ChatUI.template() : '<div class="empty">Chat module not loaded.</div>';
    if (window.ChatUI) window.ChatUI.mount();
  }

  const VIEWS = { overview: renderOverview, products: renderProducts, lowstock: renderLowStock, outofstock: renderOutOfStock, topsellers: renderTopSellers, sales: renderSales, reorder: renderReorder, settings: renderSettings, chat: renderChat };

  function switchView(name) {
    const D = window.PRODUCTS_DATA;
    $('view-title').textContent = TITLES[name] || 'Dashboard';
    $('content').classList.toggle('chat-mode', name === 'chat');
    document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.view === name));
    (VIEWS[name] || renderOverview)(D);
  }

  async function init() {
    const D = await loadData();
    if (!D) {
      $('content').innerHTML = '<div class="empty">No data available. Run <code>python scripts/init_db.py</code>, then start the backend (<code>uvicorn src.api.main:app</code>) or regenerate the snapshot.</div>';
      return;
    }
    window.PRODUCTS_DATA = D;
    if (!D.config) D.config = {};

    const badge = $('model-badge');
    if (badge) {
      badge.textContent = D.config.LLM_MODEL || 'no model';
      badge.classList.add(window.APP_MODE === 'live' ? 'live' : 'snapshot');
      badge.title = window.APP_MODE === 'live'
        ? 'Live data — FastAPI backend connected'
        : 'Static snapshot — start the backend for live data and the real agent';
    }
    $('generated-at').textContent = (window.APP_MODE === 'live' ? 'Live · ' : 'Snapshot · ') + D.generated_at;

    document.querySelectorAll('.nav-item').forEach(btn => {
      btn.addEventListener('click', () => switchView(btn.dataset.view));
    });
    switchView('overview');

    // restore sidebar collapse state
    var sb = document.getElementById('sidebar');
    if (sb) {
      try {
        if (localStorage.getItem('inventraai_sidebar_collapsed') === '1') sb.classList.add('collapsed');
      } catch (e) { /* ignore */ }
    }
  }

  window.toggleSidebar = function () {
    var sb = document.getElementById('sidebar');
    if (!sb) return;
    if (window.innerWidth <= 860) { sb.classList.toggle('open'); return; }
    var collapsed = sb.classList.toggle('collapsed');
    try { localStorage.setItem('inventraai_sidebar_collapsed', collapsed ? '1' : '0'); } catch (e) { /* ignore */ }
  };

  document.addEventListener('DOMContentLoaded', init);
})();
