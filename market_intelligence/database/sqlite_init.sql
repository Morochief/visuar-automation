-- SQLite Adaptation of Opportunity Margin View
DROP VIEW IF EXISTS opportunity_margin_vw;

CREATE VIEW opportunity_margin_vw AS
WITH latest_prices AS (
    SELECT 
        l.competitor_product_id,
        cp.product_id,
        cp.competitor_id,
        l.price,
        l.is_in_stock,
        l.scraped_at
    FROM price_logs l
    JOIN competitor_products cp ON l.competitor_product_id = cp.id
    WHERE l.scraped_at = (
        SELECT MAX(scraped_at)
        FROM price_logs b
        WHERE b.competitor_product_id = l.competitor_product_id
    )
    AND cp.product_id IS NOT NULL
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
),
calculated AS (
    SELECT 
        p.id as product_id,
        p.name,
        p.brand,
        p.capacity_btu,
        v.visuar_price,
        b.bristol_price,
        g.gg_price,
        MIN(COALESCE(b.bristol_price, 9999999999), COALESCE(g.gg_price, 9999999999)) as lowest_comp,
        b.b_stock,
        g.g_stock,
        v.scraped_at as v_scraped_at,
        b.b_scraped_at,
        g.g_scraped_at
    FROM products p
    LEFT JOIN visuar_prices v ON p.id = v.product_id
    LEFT JOIN bristol_prices b ON p.id = b.product_id
    LEFT JOIN gg_prices g ON p.id = g.product_id
    WHERE v.visuar_price IS NOT NULL
)
SELECT 
    product_id as id,
    name,
    brand,
    capacity_btu,
    visuar_price,
    bristol_price,
    gg_price,
    lowest_comp,
    CASE 
        WHEN visuar_price > 0 AND lowest_comp < 9999999999 
        THEN ROUND(((visuar_price - lowest_comp) / lowest_comp) * 100, 2)
        ELSE NULL
    END as diff_percent,
    CASE
        WHEN lowest_comp = 9999999999 THEN 'NO_COMPETITOR_DATA'
        WHEN lowest_comp < visuar_price THEN 'LOSS'
        WHEN lowest_comp > visuar_price THEN 'WIN'
        ELSE 'EQUAL'
    END as status,
    MAX(
      COALESCE(v_scraped_at, '1970-01-01'), 
      COALESCE(b_scraped_at, '1970-01-01'), 
      COALESCE(g_scraped_at, '1970-01-01')
    ) as last_updated
FROM calculated;
