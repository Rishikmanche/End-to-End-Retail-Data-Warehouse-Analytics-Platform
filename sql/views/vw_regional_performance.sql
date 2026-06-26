-- ============================================================================
-- VIEW: vw_regional_performance
-- ============================================================================

CREATE OR REPLACE VIEW vw_regional_performance AS
SELECT 
    r.region,
    r.country,
    r.state,
    r.city,
    SUM(f.sales) AS gross_sales,
    SUM(f.revenue) AS total_revenue,
    SUM(f.profit) AS total_profit,
    SUM(f.quantity) AS total_units_sold,
    COUNT(DISTINCT f.order_id) AS total_orders,
    ROUND(SUM(f.profit) / NULLIF(SUM(f.revenue), 0), 4) AS regional_profit_margin
FROM fact_sales f
JOIN dim_region r ON f.region_key = r.region_key
GROUP BY r.region, r.country, r.state, r.city
ORDER BY r.region, total_revenue DESC;
