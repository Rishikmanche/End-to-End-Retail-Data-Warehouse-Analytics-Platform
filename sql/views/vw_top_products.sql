-- ============================================================================
-- VIEW: vw_top_products
-- ============================================================================

CREATE OR REPLACE VIEW vw_top_products AS
SELECT 
    p.product_id,
    p.product_name,
    cat.category_name,
    p.sub_category,
    SUM(f.sales) AS gross_sales,
    SUM(f.revenue) AS total_revenue,
    SUM(f.profit) AS total_profit,
    SUM(f.quantity) AS total_quantity_sold,
    ROUND(AVG(f.discount), 4) AS average_discount_rate,
    ROUND(SUM(f.profit) / NULLIF(SUM(f.revenue), 0), 4) AS product_profit_margin,
    DENSE_RANK() OVER (PARTITION BY cat.category_name ORDER BY SUM(f.revenue) DESC) AS category_revenue_rank
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.product_key
JOIN dim_category cat ON f.category_key = cat.category_key
GROUP BY p.product_id, p.product_name, cat.category_name, p.sub_category
ORDER BY total_revenue DESC;
