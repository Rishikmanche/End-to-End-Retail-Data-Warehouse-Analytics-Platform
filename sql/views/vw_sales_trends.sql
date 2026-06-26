-- ============================================================================
-- VIEW: vw_sales_trends
-- ============================================================================

CREATE OR REPLACE VIEW vw_sales_trends AS
WITH daily_sales AS (
    SELECT 
        d.full_date,
        SUM(f.revenue) AS daily_revenue,
        SUM(f.profit) AS daily_profit,
        COUNT(DISTINCT f.order_id) AS daily_orders
    FROM fact_sales f
    JOIN dim_date d ON f.order_date_key = d.date_key
    GROUP BY d.full_date
)
SELECT 
    full_date,
    daily_revenue,
    daily_profit,
    daily_orders,
    -- 7-day moving average of revenue
    ROUND(
        AVG(daily_revenue) OVER (
            ORDER BY full_date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_7day_revenue_avg,
    -- 30-day moving average of revenue
    ROUND(
        AVG(daily_revenue) OVER (
            ORDER BY full_date 
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_30day_revenue_avg,
    -- Cumulative year-to-date revenue
    ROUND(
        SUM(daily_revenue) OVER (
            PARTITION BY EXTRACT(YEAR FROM full_date)
            ORDER BY full_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ), 2
    ) AS cumulative_ytd_revenue
FROM daily_sales
ORDER BY full_date;
