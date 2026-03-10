-- Enable UUID and Encryption extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

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
('Bristol', 'https://www.bristol.com.py/'),
('Gonzalez Gimenez', 'https://www.gonzalezgimenez.com.py/')
ON CONFLICT (name) DO NOTHING;

-- Products Table (Canonical Master)
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    brand VARCHAR(100),
    capacity_btu INTEGER,
    is_inverter BOOLEAN,
    internal_cost DECIMAL(15, 2) DEFAULT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Competitor Product Table (Mapping bridge)
CREATE TABLE competitor_products (
    id SERIAL PRIMARY KEY,
    competitor_id INTEGER NOT NULL REFERENCES competitors(id),
    product_id UUID REFERENCES products(id),
    name VARCHAR(255) NOT NULL,
    capacity_btu INTEGER,
    is_inverter BOOLEAN,
    description TEXT,
    raw_brand VARCHAR(100),
    sku VARCHAR(100),
    url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Price Logs (Historical append-only facts)
CREATE TABLE price_logs (
    id SERIAL PRIMARY KEY,
    competitor_product_id INTEGER NOT NULL REFERENCES competitor_products(id),
    price DECIMAL(15, 2) NOT NULL,
    is_in_stock BOOLEAN DEFAULT TRUE,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for time-series querying speeds
CREATE INDEX idx_price_logs_product_time ON price_logs(product_id, scraped_at DESC);
CREATE INDEX idx_price_logs_competitor ON price_logs(competitor_id);

-- VIEW: Opportunity Margin (Dynamic Price Mismatch Engine)
DROP VIEW IF EXISTS opportunity_margin_vw CASCADE;
CREATE OR REPLACE VIEW opportunity_margin_vw AS
WITH latest_prices AS (
    -- Get the most recent price per product per competitor
    SELECT DISTINCT ON (cp.product_id, cp.competitor_id)
        cp.product_id,
        cp.competitor_id,
        pl.price,
        pl.is_in_stock,
        pl.scraped_at
    FROM price_logs pl
    JOIN competitor_products cp ON pl.competitor_product_id = cp.id
    WHERE cp.product_id IS NOT NULL
    ORDER BY cp.product_id, cp.competitor_id, pl.scraped_at DESC
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
),
gg_prices AS (
    SELECT lp.product_id, lp.price as gg_price, lp.is_in_stock as g_stock, lp.scraped_at as g_scraped_at
    FROM latest_prices lp
    JOIN competitors c ON lp.competitor_id = c.id
    WHERE c.name = 'Gonzalez Gimenez'
)
SELECT 
    p.id as product_id,
    p.name,
    p.brand,
    p.capacity_btu,
    p.internal_cost,
    v.visuar_price,
    b.bristol_price,
    g.gg_price,
    LEAST(b.bristol_price, g.gg_price) as lowest_comp_price,
    -- Margen Real (Visuar Price - Internal Cost)
    CASE 
        WHEN p.internal_cost > 0 AND v.visuar_price > 0 
        THEN ROUND(((v.visuar_price - p.internal_cost) / p.internal_cost) * 100, 2)
        ELSE NULL
    END as real_margin_percent,
    -- Margin: Positive means Visuar is MORE expensive. Negative means Visuar is CHEAPER.
    CASE 
        WHEN v.visuar_price > 0 AND LEAST(b.bristol_price, g.gg_price) IS NOT NULL 
        THEN ROUND(((v.visuar_price - LEAST(b.bristol_price, g.gg_price)) / LEAST(b.bristol_price, g.gg_price)) * 100, 2)
        ELSE NULL
    END as diff_percent,
    CASE
        WHEN LEAST(b.bristol_price, g.gg_price) < v.visuar_price THEN 'LOSS'
        WHEN LEAST(b.bristol_price, g.gg_price) > v.visuar_price THEN 'WIN'
        ELSE 'EQUAL'
    END as status,
    COALESCE(GREATEST(v.scraped_at, b.b_scraped_at, g.g_scraped_at), v.scraped_at) as last_updated
FROM products p
LEFT JOIN visuar_prices v ON p.id = v.product_id
LEFT JOIN bristol_prices b ON p.id = b.product_id
LEFT JOIN gg_prices g ON p.id = g.product_id
WHERE v.visuar_price IS NOT NULL;

-- Índice compuesto para optimizar las consultas históricas del Dashboard
CREATE INDEX IF NOT EXISTS idx_price_logs_product_date 
ON price_logs(product_id, scraped_at DESC);

-- Tabla para monitorear la salud y resiliencia del scraper
CREATE TABLE scrape_logs (
    id SERIAL PRIMARY KEY,
    competitor_id INTEGER REFERENCES competitors(id),
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20), -- 'success', 'partial', 'failed'
    products_scraped INTEGER,
    error_message TEXT
);

-- Índice requerido para el Dashboard: 'última ejecución por competidor'
CREATE INDEX IF NOT EXISTS idx_scrape_logs_competitor_status 
ON scrape_logs(competitor_id, started_at DESC);

-- Tabla para registrar reglas de alerta configuradas
CREATE TABLE alert_rules (
    id SERIAL PRIMARY KEY,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    competitor_id INTEGER REFERENCES competitors(id), -- Opcional, NULL = cualquier competidor
    target_price DECIMAL(15, 2), -- Notificar si el precio es menor o igual a este
    notify_on_stock_change BOOLEAN DEFAULT FALSE,
    notification_channel VARCHAR(50) DEFAULT 'email', -- MVP: Solo 'email' o 'telegram'
    -- NOTA SEGURIDAD: Columna encriptada mediante pgp_sym_encrypt()
    contact_info BYTEA NOT NULL, 
    cooldown_hours INTEGER DEFAULT 24, -- Ventana flexible para no re-enviar la misma alerta
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para llevar el registro de notificaciones enviadas y snapshot de configuración
CREATE TABLE notifications_log (
    id SERIAL PRIMARY KEY,
    alert_rule_id INTEGER REFERENCES alert_rules(id) ON DELETE CASCADE,
    price_log_id INTEGER REFERENCES price_logs(id),
    rule_snapshot JSONB NOT NULL, -- Guarda la configuración (target_price, etc) al momento del disparo
    message_sent TEXT NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
