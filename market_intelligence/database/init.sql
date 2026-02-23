-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Competitors Table (Metadata)
CREATE TABLE competitors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    url VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed Initial Competitors
INSERT INTO competitors (name, url) VALUES 
('Visuar', 'https://www.visuar.com.py/'),
('Bristol', 'https://www.bristol.com.py/')
ON CONFLICT (name) DO NOTHING;

-- Products Table (Canonical Master)
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    brand VARCHAR(100),
    capacity_btu INTEGER,
    is_inverter BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Price Logs (Historical append-only facts)
CREATE TABLE price_logs (
    id SERIAL PRIMARY KEY,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    competitor_id INTEGER REFERENCES competitors(id),
    price DECIMAL(15, 2) NOT NULL,
    is_in_stock BOOLEAN DEFAULT TRUE,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for time-series querying speeds
CREATE INDEX idx_price_logs_product_time ON price_logs(product_id, scraped_at DESC);
CREATE INDEX idx_price_logs_competitor ON price_logs(competitor_id);

-- VIEW: Opportunity Margin (Dynamic Price Mismatch Engine)
CREATE OR REPLACE VIEW opportunity_margin_vw AS
WITH latest_prices AS (
    -- Get the most recent price per product per competitor
    SELECT DISTINCT ON (product_id, competitor_id)
        product_id,
        competitor_id,
        price,
        is_in_stock,
        scraped_at
    FROM price_logs
    ORDER BY product_id, competitor_id, scraped_at DESC
),
visuar_prices AS (
    SELECT lp.product_id, lp.price as visuar_price, lp.is_in_stock as v_stock, lp.scraped_at
    FROM latest_prices lp
    JOIN competitors c ON lp.competitor_id = c.id
    WHERE c.name = 'Visuar'
),
bristol_prices AS (
    SELECT lp.product_id, lp.price as bristol_price, lp.is_in_stock as b_stock, lp.scraped_at as b_scraped_at
    FROM latest_prices lp
    JOIN competitors c ON lp.competitor_id = c.id
    WHERE c.name = 'Bristol'
)
SELECT 
    p.id as product_id,
    p.name,
    p.brand,
    p.capacity_btu,
    v.visuar_price,
    b.bristol_price,
    -- Margin: Positive means Visuar is MORE expensive. Negative means Visuar is CHEAPER.
    CASE 
        WHEN v.visuar_price > 0 AND b.bristol_price IS NOT NULL 
        THEN ROUND(((v.visuar_price - b.bristol_price) / b.bristol_price) * 100, 2)
        ELSE NULL
    END as diff_percent,
    CASE
        WHEN b.b_stock = FALSE THEN 'COMPETITOR_OUT_OF_STOCK'
        WHEN b.bristol_price < v.visuar_price THEN 'LOSS'
        WHEN b.bristol_price > v.visuar_price THEN 'WIN'
        ELSE 'EQUAL'
    END as status,
    GREATEST(v.scraped_at, b.b_scraped_at) as last_updated
FROM products p
LEFT JOIN visuar_prices v ON p.id = v.product_id
LEFT JOIN bristol_prices b ON p.id = b.product_id
WHERE v.visuar_price IS NOT NULL;
