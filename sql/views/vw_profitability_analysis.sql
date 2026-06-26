-- ============================================================================
-- VIEW: vw_profitability_analysis
-- ============================================================================

CREATE OR REPLACE VIEW vw_profitability_analysis AS
SELECT 
    cat.category_name,
    p.sub_category,
    p.product_id,
    p.product_name,
    SUM(f.sales) AS gross_sales,
    SUM(f.revenue) AS total_revenue,
    SUM(f.profit) AS total_profit,
    SUM(f.quantity) AS total_units_sold,
    ROUND(SUM(f.profit) / NULLIF(SUM(f.revenue), 0), 4) AS profit_margin,
    -- Impact of discounts
    ROUND(SUM(f.sales - f.revenue), 2) AS total_discounts_granted,
    ROUND(AVG(f.discount), 4) AS average_discount_rate
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.product_key
JOIN dim_category cat ON f.category_key = cat.category_key
GROUP BY cat.category_name, p.sub_category, p.product_id, p.product_name
ORDER BY total_profit DESC;
