"""SQLite database schema for the application."""

_SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (category_id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY, price_brl REAL NOT NULL, name TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(category_id), description TEXT NOT NULL,
    stock_quantity INTEGER NOT NULL, status TEXT NOT NULL, specs TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS promotions (
    promotion_id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(product_id),
    discount_percent REAL NOT NULL, description TEXT NOT NULL, is_active INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL, email TEXT NOT NULL, city TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date TEXT NOT NULL, status TEXT NOT NULL, total_brl REAL NOT NULL, payment_method TEXT NOT NULL,
    tracking_code TEXT, estimated_delivery TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS order_items (
    order_id INTEGER NOT NULL REFERENCES orders(order_id), product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL, PRIMARY KEY (order_id, product_id)
);
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY, channel_phone TEXT NOT NULL, customer_id INTEGER REFERENCES customers(customer_id),
    access_level INTEGER NOT NULL CHECK (access_level BETWEEN 0 AND 2), policy_version TEXT NOT NULL,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(session_id), role TEXT NOT NULL,
    content TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS messages_by_session ON messages(session_id, created_at, message_id);
CREATE TABLE IF NOT EXISTS rate_limits (
    rate_limit_key TEXT PRIMARY KEY, window_started_at TEXT NOT NULL, request_count INTEGER NOT NULL
);
"""
