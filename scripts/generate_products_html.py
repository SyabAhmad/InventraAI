"""Generate a self-contained HTML product dashboard from the SQLite database.

Phase-1 compatible: reads the database directly (no service layer needed).
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import DATABASE_PATH


def _conn():
    c = sqlite3.connect(DATABASE_PATH)
    c.row_factory = sqlite3.Row
    return c


def build_data() -> dict:
    conn = _conn()
    try:
        products = [dict(r) for r in conn.execute(
            """SELECT p.product_id, p.sku, p.name, p.category, p.price, p.cost,
                      p.min_stock_threshold, p.supplier,
                      COALESCE(i.current_stock,0) AS current_stock, i.last_updated
               FROM products p LEFT JOIN inventory i ON p.product_id=i.product_id
               ORDER BY p.product_id;"""
        ).fetchall()]

        total_stock = conn.execute("SELECT COALESCE(SUM(current_stock),0) FROM inventory;").fetchone()[0]
        low_count = conn.execute(
            """SELECT COUNT(*) FROM products p JOIN inventory i ON p.product_id=i.product_id
               WHERE i.current_stock < p.min_stock_threshold;"""
        ).fetchone()[0]
        out_count = conn.execute("SELECT COUNT(*) FROM inventory WHERE current_stock=0;").fetchone()[0]
        total_value = conn.execute(
            """SELECT COALESCE(SUM(i.current_stock * p.price),0)
               FROM products p JOIN inventory i ON p.product_id=i.product_id;"""
        ).fetchone()[0]

        low_stock = [dict(r) for r in conn.execute(
            """SELECT p.product_id, p.sku, p.name, p.category, p.price,
                      p.min_stock_threshold, COALESCE(i.current_stock,0) AS current_stock
               FROM products p JOIN inventory i ON p.product_id=i.product_id
               WHERE i.current_stock < p.min_stock_threshold
               ORDER BY i.current_stock ASC;"""
        ).fetchall()]
        out_of_stock = [dict(r) for r in conn.execute(
            """SELECT p.product_id, p.sku, p.name, p.category, p.price,
                      p.min_stock_threshold, COALESCE(i.current_stock,0) AS current_stock
               FROM products p JOIN inventory i ON p.product_id=i.product_id
               WHERE i.current_stock = 0 ORDER BY p.name;"""
        ).fetchall()]

        # sales totals per product
        sales_rows = conn.execute(
            """SELECT product_id, COALESCE(SUM(quantity),0) AS units, COALESCE(SUM(quantity*unit_price),0) AS rev
               FROM sales GROUP BY product_id;"""
        ).fetchall()
        sales_map = {r["product_id"]: {"units": r["units"], "rev": r["rev"]} for r in sales_rows}
        for p in products:
            s = sales_map.get(p["product_id"], {})
            p["total_units_sold"] = int(s.get("units", 0))
            p["total_revenue"] = float(s.get("rev", 0) or 0)

        top_rows = conn.execute(
            """SELECT s.product_id, SUM(s.quantity) AS total_units, SUM(s.quantity*s.unit_price) AS total_revenue
               FROM sales s GROUP BY s.product_id ORDER BY total_units DESC LIMIT 10;"""
        ).fetchall()
        top_sellers = []
        for r in top_rows:
            prod = next((p for p in products if p["product_id"] == r["product_id"]), None)
            if prod:
                top_sellers.append({
                    "product_id": r["product_id"],
                    "name": prod["name"],
                    "category": prod["category"],
                    "total_units": int(r["total_units"]),
                    "total_revenue": float(r["total_revenue"] or 0),
                })
    finally:
        conn.close()

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "summary": {
            "total_products": len(products),
            "total_stock_units": int(total_stock),
            "low_stock_count": int(low_count),
            "out_of_stock_count": int(out_count),
            "inventory_value_at_price": round(float(total_value), 2),
        },
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
        "top_sellers": top_sellers,
        "products": products,
    }


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>InventraAI — Products Dashboard</title>
<style>
  :root {
    --bg: #0f172a; --card: #1e293b; --card2: #334155;
    --text: #e2e8f0; --muted: #94a3b8; --accent: #38bdf8;
    --green: #22c55e; --yellow: #eab308; --red: #ef4444; --border: #334155;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.5; }
  header { padding: 24px 32px; background: linear-gradient(135deg, #1e293b, #0f172a); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
  header h1 { margin: 0; font-size: 24px; }
  header .sub { color: var(--muted); font-size: 14px; }
  .badge { background: var(--accent); color: #0f172a; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }
  .container { max-width: 1400px; margin: 0 auto; padding: 24px 32px; }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 18px; }
  .card .label { color: var(--muted); font-size: 13px; text-transform: uppercase; letter-spacing: .5px; }
  .card .value { font-size: 28px; font-weight: 700; margin-top: 6px; }
  .card .hint { color: var(--muted); font-size: 12px; margin-top: 4px; }
  .section { margin-bottom: 32px; }
  .section h2 { font-size: 18px; margin: 0 0 12px; }
  .toolbar { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
  .toolbar input, .toolbar select { background: var(--card); border: 1px solid var(--border); color: var(--text); padding: 8px 12px; border-radius: 8px; font-size: 14px; }
  .toolbar input { flex: 1; min-width: 200px; }
  table { width: 100%; border-collapse: collapse; background: var(--card); border-radius: 12px; overflow: hidden; }
  th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); font-size: 14px; }
  th { background: var(--card2); color: var(--muted); font-weight: 600; cursor: pointer; user-select: none; }
  th:hover { color: var(--text); }
  tr:hover { background: #273549; }
  .status { display: inline-block; padding: 3px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; }
  .status.ok { background: rgba(34,197,94,.15); color: var(--green); }
  .status.low { background: rgba(234,179,8,.15); color: var(--yellow); }
  .status.out { background: rgba(239,68,68,.15); color: var(--red); }
  .alert-list { display: grid; gap: 8px; }
  .alert-item { background: var(--card); border-left: 4px solid var(--red); padding: 10px 14px; border-radius: 8px; font-size: 14px; }
  .alert-item.low { border-left-color: var(--yellow); }
  .top-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
  .top-item { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 12px; }
  .top-item .name { font-weight: 600; }
  .top-item .meta { color: var(--muted); font-size: 12px; margin-top: 4px; }
  .num { text-align: right; }
  footer { text-align: center; color: var(--muted); font-size: 12px; padding: 24px; }
  .empty { color: var(--muted); font-style: italic; padding: 12px; }
</style>
</head>
<body>
<header>
  <div>
    <h1>InventraAI <span class="badge">Phase 1</span></h1>
    <div class="sub">Products & Inventory Dashboard — sample e-commerce data</div>
  </div>
  <div class="sub">Generated: __GENERATED_AT__</div>
</header>

<div class="container">
  <div class="cards">
    <div class="card"><div class="label">Total Products</div><div class="value" id="c-products">0</div><div class="hint">In catalogue</div></div>
    <div class="card"><div class="label">Total Stock Units</div><div class="value" id="c-stock">0</div><div class="hint">Across all products</div></div>
    <div class="card"><div class="label">Low Stock</div><div class="value" id="c-low" style="color:var(--yellow)">0</div><div class="hint">Below minimum threshold</div></div>
    <div class="card"><div class="label">Out of Stock</div><div class="value" id="c-out" style="color:var(--red)">0</div><div class="hint">Zero units available</div></div>
    <div class="card"><div class="label">Inventory Value</div><div class="value" id="c-value">0</div><div class="hint">At selling price</div></div>
  </div>

  <div class="section">
    <h2>Low-Stock Alerts</h2>
    <div class="alert-list" id="low-alerts"></div>
  </div>

  <div class="section">
    <h2>Top Sellers (by units)</h2>
    <div class="top-list" id="top-sellers"></div>
  </div>

  <div class="section">
    <h2>All Products</h2>
    <div class="toolbar">
      <input type="text" id="search" placeholder="Search by name, SKU, or category..." />
      <select id="cat-filter"><option value="">All categories</option></select>
      <select id="status-filter">
        <option value="">All statuses</option>
        <option value="ok">Healthy</option>
        <option value="low">Low stock</option>
        <option value="out">Out of stock</option>
      </select>
      <select id="sort">
        <option value="name">Sort: Name</option>
        <option value="stock-asc">Sort: Stock (low first)</option>
        <option value="stock-desc">Sort: Stock (high first)</option>
        <option value="price-desc">Sort: Price (high first)</option>
        <option value="sold-desc">Sort: Units sold (high first)</option>
      </select>
    </div>
    <table>
      <thead>
        <tr><th>SKU</th><th>Name</th><th>Category</th><th class="num">Price</th><th class="num">Stock</th><th class="num">Min</th><th>Status</th><th class="num">Units Sold</th><th class="num">Revenue</th></tr>
      </thead>
      <tbody id="tbody"></tbody>
    </table>
    <div class="empty" id="empty-msg" style="display:none">No products match your filters.</div>
  </div>
</div>

<footer>InventraAI — Phase 1 Foundation · Sample data for FYP demonstration</footer>

<script>
const DATA = __DATA_JSON__;

document.getElementById('c-products').textContent = DATA.summary.total_products.toLocaleString();
document.getElementById('c-stock').textContent = DATA.summary.total_stock_units.toLocaleString();
document.getElementById('c-low').textContent = DATA.summary.low_stock_count.toLocaleString();
document.getElementById('c-out').textContent = DATA.summary.out_of_stock_count.toLocaleString();
document.getElementById('c-value').textContent = '$' + DATA.summary.inventory_value_at_price.toLocaleString();

const alertsEl = document.getElementById('low-alerts');
const lowItems = [...DATA.low_stock, ...DATA.out_of_stock].slice(0, 12);
if (lowItems.length === 0) alertsEl.innerHTML = '<div class="empty">No low-stock items 🎉</div>';
else lowItems.forEach(p => {
  const div = document.createElement('div');
  div.className = 'alert-item' + (p.current_stock === 0 ? '' : ' low');
  div.innerHTML = `<strong>${p.name}</strong> (${p.sku}) — ${p.current_stock} units left (min ${p.min_stock_threshold}) · ${p.category}`;
  alertsEl.appendChild(div);
});

const topEl = document.getElementById('top-sellers');
DATA.top_sellers.slice(0, 8).forEach((t, i) => {
  const div = document.createElement('div');
  div.className = 'top-item';
  div.innerHTML = `<div class="name">#${i+1} ${t.name}</div><div class="meta">${t.category} · ${t.total_units} units · $${Number(t.total_revenue).toFixed(2)}</div>`;
  topEl.appendChild(div);
});

const cats = [...new Set(DATA.products.map(p => p.category))].sort();
const catSel = document.getElementById('cat-filter');
cats.forEach(c => { const o = document.createElement('option'); o.value = c; o.textContent = c; catSel.appendChild(o); });

function statusOf(p) { if (p.current_stock === 0) return 'out'; if (p.current_stock < p.min_stock_threshold) return 'low'; return 'ok'; }
function statusLabel(s) { return s === 'out' ? 'Out' : s === 'low' ? 'Low' : 'OK'; }

function render() {
  const q = document.getElementById('search').value.toLowerCase();
  const cat = document.getElementById('cat-filter').value;
  const st = document.getElementById('status-filter').value;
  const sort = document.getElementById('sort').value;
  let rows = DATA.products.filter(p => {
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
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = '';
  rows.forEach(p => {
    const s = statusOf(p);
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${p.sku}</td><td>${p.name}</td><td>${p.category}</td><td class="num">$${p.price.toFixed(2)}</td><td class="num">${p.current_stock}</td><td class="num">${p.min_stock_threshold}</td><td><span class="status ${s}">${statusLabel(s)}</span></td><td class="num">${p.total_units_sold || 0}</td><td class="num">$${(p.total_revenue || 0).toFixed(2)}</td>`;
    tbody.appendChild(tr);
  });
  document.getElementById('empty-msg').style.display = rows.length ? 'none' : 'block';
}

['search','cat-filter','status-filter','sort'].forEach(id => {
  document.getElementById(id).addEventListener('input', render);
  document.getElementById(id).addEventListener('change', render);
});
render();
</script>
</body>
</html>
"""


def main():
    data = build_data()
    html = HTML_TEMPLATE.replace("__GENERATED_AT__", data["generated_at"])
    html = html.replace("__DATA_JSON__", json.dumps(data))
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "index.html")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("Generated:", out_path)
    print("Products:", len(data["products"]), "| Low stock:", data["summary"]["low_stock_count"], "| Out of stock:", data["summary"]["out_of_stock_count"])


if __name__ == "__main__":
    main()