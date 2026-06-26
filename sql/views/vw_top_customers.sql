-- ============================================================================
-- VIEW: vw_top_customers
-- ============================================================================

CREATE OR REPLACE VIEW vw_top_customers AS
SELECT 
    c.customer_id,
    c.customer_name,
    c.segment AS market_segment,
    SUM(f.sales) AS gross_sales,
    SUM(f.revenue) AS total_revenue,
    SUM(f.profit) AS total_profit,
    COUNT(DISTINCT f.order_id) AS total_orders,
    SUM(f.quantity) AS total_units_purchased,
    ROUND(SUM(f.revenue) / NULLIF(COUNT(DISTINCT f.order_id), 0), 2) AS average_order_value,
    ROUND(SUM(f.profit) / NULLIF(SUM(f.revenue), 0), 4) AS customer_profit_margin,
    DENSE_RANK() OVER (ORDER BY SUM(f.revenue) DESC) as customer_revenue_rank
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
GROUP BY c.customer_id, c.customer_name, c.segment
ORDER BY total_revenue DESC;
