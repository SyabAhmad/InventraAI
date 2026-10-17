/* InventraAI dashboard rendering components */
(function () {
  'use strict';

  function $(id) { return document.getElementById(id); }

  function statusOf(p) {
    if (p.current_stock === 0) return 'out';
    if (p.current_stock < p.min_stock_threshold) return 'low';
    return 'ok';
  }
  function statusLabel(s) { return s === 'out' ? 'Out' : s === 'low' ? 'Low' : 'OK'; }

  function renderCards(summary) {
    $('cards').innerHTML = `
      <div class="card"><div class="label">Total Products</div><div class="value">${summary.total_products.toLocaleString()}</div><div class="hint">In catalogue</div></div>
      <div class="card"><div class="label">Total Stock Units</div><div class="value">${summary.total_stock_units.toLocaleString()}</div><div class="hint">Across all products</div></div>
      <div class="card"><div class="label">Low Stock</div><div class="value" style="color:var(--yellow)">${summary.low_stock_count.toLocaleString()}</div><div class="hint">Below minimum threshold</div></div>
      <div class="card"><div class="label">Out of Stock</div><div class="value" style="color:var(--red)">${summary.out_of_stock_count.toLocaleString()}</div><div class="hint">Zero units available</div></div>
      <div class="card"><div class="label">Inventory Value</div><div class="value">$${summary.inventory_value_at_price.toLocaleString()}</div><div class="hint">At selling price</div></div>`;
  }

  function renderAlerts(lowStock, outOfStock) {
    const el = $('low-alerts');
    const items = [...lowStock, ...outOfStock].slice(0, 12);
    if (!items.length) { el.innerHTML = '<div class="empty">No low-stock items 🎉</div>'; return; }
    el.innerHTML = items.map(p =>
      `<div class="alert-item${p.current_stock === 0 ? '' : ' low'}">
        <strong>${p.name}</strong> (${p.sku}) — ${p.current_stock} units left (min ${p.min_stock_threshold}) · ${p.category}
      </div>`).join('');
  }

  function renderTopSellers(list) {
    const el = $('top-sellers');
    el.innerHTML = list.slice(0, 8).map((t, i) =>
      `<div class="top-item">
        <div class="name">#${i + 1} ${t.name}</div>
        <div class="meta">${t.category} · ${t.total_units} units · $${Number(t.total_revenue).toFixed(2)}</div>
      </div>`).join('');
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

    const tbody = $('tbody');
    tbody.innerHTML = rows.map(p => {
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

  function init() {
    const DATA = window.PRODUCTS_DATA;
    if (!DATA) { console.error('PRODUCTS_DATA not loaded'); return; }
    $('generated-at').textContent = 'Generated: ' + DATA.generated_at;

    renderCards(DATA.summary);
    renderAlerts(DATA.low_stock, DATA.out_of_stock);
    renderTopSellers(DATA.top_sellers);

    const cats = [...new Set(DATA.products.map(p => p.category))].sort();
    const catSel = $('cat-filter');
    cats.forEach(c => { const o = document.createElement('option'); o.value = c; o.textContent = c; catSel.appendChild(o); });

    const rerender = () => renderTable(DATA.products);
    ['search', 'cat-filter', 'status-filter', 'sort'].forEach(id => {
      $(id).addEventListener('input', rerender);
      $(id).addEventListener('change', rerender);
    });
    renderTable(DATA.products);
  }

  document.addEventListener('DOMContentLoaded', init);
})();