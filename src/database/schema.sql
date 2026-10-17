-- AI Inventory Management Agent - SQLite Schema

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS products (
    product_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sku                 TEXT    NOT NULL UNIQUE,
    name                TEXT    NOT NULL,
    category            TEXT    NOT NULL,
    price               REAL    NOT NULL,
    cost                REAL    NOT NULL,
    min_stock_threshold INTEGER NOT NULL DEFAULT 20,
    supplier            TEXT,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS inventory (
    product_id   INTEGER PRIMARY KEY,
    current_stock INTEGER NOT NULL DEFAULT 0,
    last_updated TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sales (
    sale_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    quantity   INTEGER NOT NULL,
    unit_price REAL    NOT NULL,
    sale_date  TEXT    NOT NULL,
    channel    TEXT    DEFAULT 'web',
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reorder_history (
    rec_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id       INTEGER NOT NULL,
    recommended_qty  INTEGER NOT NULL,
    reason           TEXT,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now')),
    status           TEXT    DEFAULT 'suggested',
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sales_product_date ON sales(product_id, sale_date);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);