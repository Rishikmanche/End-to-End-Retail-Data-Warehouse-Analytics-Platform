-- ============================================================================
-- VIEW: vw_revenue_by_month
-- ============================================================================

CREATE OR REPLACE VIEW vw_revenue_by_month AS
SELECT 
    d.year,
    d.month,
    d.month_name,
    SUM(f.sales) AS gross_sales,
    SUM(f.revenue) AS net_revenue,
    SUM(f.profit) AS total_profit,
    SUM(f.quantity) AS total_units_sold,
    COUNT(DISTINCT f.order_id) AS total_orders,
    ROUND(SUM(f.revenue) / NULLIF(COUNT(DISTINCT f.order_id), 0), 2) AS average_order_value,
    ROUND(SUM(f.profit) / NULLIF(SUM(f.revenue), 0), 4) AS net_profit_margin
FROM fact_sales f
JOIN dim_date d ON f.order_date_key = d.date_key
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;
