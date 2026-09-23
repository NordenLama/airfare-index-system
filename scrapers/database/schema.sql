-- 1. Table for Live Scraped Fares (Dynamic Market Data P_t)
CREATE TABLE IF NOT EXISTS live_fares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scrape_timestamp DATETIME NOT NULL,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    airline TEXT NOT NULL,
    flight_number TEXT,
    price REAL NOT NULL,
    departure_time DATETIME,
    booking_lead_days INTEGER NOT NULL,
    flight_type TEXT DEFAULT 'Direct',
    cabin_class TEXT DEFAULT 'economy',
    source TEXT DEFAULT 'fast-flights'
);

-- 2. Table for Static DGCA Route Weights (W_0)
CREATE TABLE IF NOT EXISTS route_weights (
    route_id TEXT PRIMARY KEY, -- e.g., 'DEL-BOM'
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    weight REAL NOT NULL       -- Weight share (e.g., 0.35)
);

-- 3. Table for Base Period Prices (P_0)
CREATE TABLE IF NOT EXISTS base_prices (
    route_id TEXT PRIMARY KEY, -- e.g., 'DEL-BOM'
    base_price REAL NOT NULL   -- Base period benchmark fare (P_0)
);

-- Insert Default Baseline Reference Data
INSERT OR IGNORE INTO route_weights (route_id, origin, destination, weight) VALUES
('DEL-BOM', 'DEL', 'BOM', 0.45),
('DEL-BLR', 'DEL', 'BLR', 0.35),
('BOM-MAA', 'BOM', 'MAA', 0.20);

INSERT OR IGNORE INTO base_prices (route_id, base_price) VALUES
('DEL-BOM', 4000.0),
('DEL-BLR', 4800.0),
('BOM-MAA', 3500.0);