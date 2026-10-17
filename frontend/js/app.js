/* InventraAI dashboard — view router + components */
(function () {
  'use strict';

  function $(id) { return document.getElementById(id); }
  function statusOf(p) {
    if (p.current_stock === 0) return 'out';
    if (p.current_stock < p.min_stock_threshold) return 'low';
    return 'ok';
  }
  function statusLabel(s) { return s === 'out' ? 'Out' : s === 'low' ? 'Low' : 'OK'; }

  const TITLES = {
    overview: 'Dashboard', products: 'Products', lowstock: 'Low Stock',
    outofstock: 'Out of Stock', topsellers: 'Top Sellers',
    sales: 'Sales Summary', settings: 'Settings', chat: 'Chat',
  };

  function card(label, value, hint, color) {
    return `<div class="card"><div class="label">${label}</div><div class="value" ${color ? `style="color:${color}"` : ''}>${value}</div><div class="hint">${hint}</div></div>`;
  }

  function renderOverview(D) {
    const s = D.summary;
    const needsAttention = s.out_of_stock_count > 0 || s.low_stock_count > 0;
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
            <strong>${p.name}</strong> <span style="color:var(--muted)">(${p.sku})</span>
            <div class="meta">${p.category} · min threshold ${p.min_stock_threshold} · $${p.price.toFixed(2)}</div>
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
      `<div class="top-item"><div class="name">#${i + 1} ${t.name}</div>
       <div class="meta">${t.category} · ${t.total_units} units · $${Number(t.total_revenue).toFixed(2)}</div></div>`).join('');
  }

  function renderProducts(D) {
    const cats = [...new Set(D.products.map(p => p.category))].sort();
    $('content').innerHTML = `
      <div class="section">
        <div class="toolbar">
          <input type="text" id="search" placeholder="Search by name, SKU, or category..." />
          <select id="cat-filter"><option value="">All categories</option>${cats.map(c => `<option value="${c}">${c}</option>`).join('')}</select>
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
      </div>`;
    const rerender = () => renderTable(D.products);
    ['search', 'cat-filter', 'status-filter', 'sort'].forEach(id => {
      $(id).addEventListener('input', rerender);
      $(id).addEventListener('change', rerender);
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
      return `<tr>
        <td>${p.sku}</td><td>${p.name}</td><td>${p.category}</td>
        <td class="num">$${p.price.toFixed(2)}</td><td class="num">${p.current_stock}</td><td class="num">${p.min_stock_threshold}</td>
        <td><span class="status ${s}">${statusLabel(s)}</span></td>
        <td class="num">${p.total_units_sold || 0}</td><td class="num">$${(p.total_revenue || 0).toFixed(2)}</td>
      </tr>`;
    }).join('');
    $('empty-msg').style.display = rows.length ? 'none' : 'block';
  }

  function renderLowStock(D) {
    const items = D.low_stock;
    $('content').innerHTML = `
      <div class="section"><h2>Low-Stock Products (${items.length})</h2>
        <div class="alert-list">${items.length ? items.map(p =>
          `<div class="alert-item low"><strong>${p.name}</strong> (${p.sku}) — ${p.current_stock} units left (min ${p.min_stock_threshold}) · ${p.category} · $${p.price.toFixed(2)}</div>`).join('') : '<div class="empty">No low-stock items 🎉</div>'}
        </div>
      </div>`;
  }

  function renderOutOfStock(D) {
    const items = D.out_of_stock;
    $('content').innerHTML = `
      <div class="section"><h2>Out-of-Stock Products (${items.length})</h2>
        <div class="alert-list">${items.length ? items.map(p =>
          `<div class="alert-item"><strong>${p.name}</strong> (${p.sku}) — 0 units · ${p.category} · $${p.price.toFixed(2)}</div>`).join('') : '<div class="empty">No out-of-stock items 🎉</div>'}
        </div>
      </div>`;
  }

  function renderTopSellers(D) {
    $('content').innerHTML = `
      <div class="section"><h2>Top Sellers by Units Sold</h2>
        <div class="top-list">${D.top_sellers.map((t, i) =>
          `<div class="top-item"><div class="name">#${i + 1} ${t.name}</div><div class="meta">${t.category} · ${t.total_units} units · $${Number(t.total_revenue).toFixed(2)}</div></div>`).join('')}
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
      <div class="section"><h2>Revenue by Category</h2>
        <div class="top-list">${Object.entries(cats).sort((a,b)=>b[1]-a[1]).map(([c,v]) =>
          `<div class="top-item"><div class="name">${c}</div><div class="meta">$${v.toFixed(2)}</div></div>`).join('')}
        </div>
      </div>`;
  }

  function renderSettings(D) {
    $('content').innerHTML = `
      <div class="section"><h2>Configuration (from .env)</h2>
        <div class="kv">
          <div><div class="k">LLM Provider</div><div class="v">${D.config ? D.config.LLM_PROVIDER : '—'}</div></div>
          <div><div class="k">LLM Model</div><div class="v">${D.config ? D.config.LLM_MODEL : '—'}</div></div>
          <div><div class="k">LLM Base URL</div><div class="v">${D.config ? D.config.LLM_BASE_URL : '—'}</div></div>
          <div><div class="k">Database</div><div class="v">${D.config ? D.config.DATABASE_PATH : '—'}</div></div>
          <div><div class="k">Default Min Stock</div><div class="v">${D.config ? D.config.DEFAULT_MIN_STOCK : '—'}</div></div>
          <div><div class="k">Forecast Horizon</div><div class="v">${D.config ? D.config.FORECAST_HORIZON_DAYS + ' days' : '—'}</div></div>
        </div>
        <p class="empty" style="margin-top:12px">Edit <code>.env</code> to change these values, then regenerate the dashboard.</p>
      </div>`;
  }

  function renderChat() {
    $('content').classList.add('chat-mode');
    $('content').innerHTML = window.ChatUI ? window.ChatUI.template() : '<div class="empty">Chat module not loaded.</div>';
    if (window.ChatUI) window.ChatUI.mount();
  }

  const VIEWS = { overview: renderOverview, products: renderProducts, lowstock: renderLowStock, outofstock: renderOutOfStock, topsellers: renderTopSellers, sales: renderSales, settings: renderSettings, chat: renderChat };

  function switchView(name) {
    const D = window.PRODUCTS_DATA;
    $('view-title').textContent = TITLES[name] || 'Dashboard';
    $('content').classList.toggle('chat-mode', name === 'chat');
    document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.view === name));
    (VIEWS[name] || renderOverview)(D);
  }

  function init() {
    const D = window.PRODUCTS_DATA;
    if (!D) { console.error('PRODUCTS_DATA not loaded'); return; }
    $('generated-at').textContent = 'Generated: ' + D.generated_at;
    if (!D.config) D.config = {};

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