-- ============================================================================
-- VIEW: vw_customer_segmentation (RFM Analysis)
-- ============================================================================

CREATE OR REPLACE VIEW vw_customer_segmentation AS
WITH customer_metrics AS (
    SELECT 
        c.customer_key,
        c.customer_id,
        c.customer_name,
        c.segment AS market_segment,
        MAX(d.full_date) AS last_order_date,
        COUNT(DISTINCT f.order_id) AS order_frequency,
        SUM(f.revenue) AS monetary_value
    FROM fact_sales f
    JOIN dim_customer c ON f.customer_key = c.customer_key
    JOIN dim_date d ON f.order_date_key = d.date_key
    GROUP BY c.customer_key, c.customer_id, c.customer_name, c.segment
),
reference_date AS (
    SELECT MAX(last_order_date) AS max_date FROM customer_metrics
),
rfm_raw_scores AS (
    SELECT 
        m.*,
        (SELECT max_date FROM reference_date) - m.last_order_date AS recency_days,
        NTILE(4) OVER (ORDER BY (SELECT max_date FROM reference_date) - m.last_order_date DESC) AS r_score, -- 4: most recent (lowest days)
        NTILE(4) OVER (ORDER BY m.order_frequency ASC) AS f_score, -- 4: highest frequency
        NTILE(4) OVER (ORDER BY m.monetary_value ASC) AS m_score -- 4: highest spending
    FROM customer_metrics m
)
SELECT 
    customer_id,
    customer_name,
    market_segment,
    last_order_date,
    recency_days,
    order_frequency,
    monetary_value,
    (r_score + f_score + m_score) AS rfm_total_score,
    r_score,
    f_score,
    m_score,
    CASE 
        WHEN (r_score + f_score + m_score) >= 10 THEN 'Champions'
        WHEN (r_score + f_score + m_score) >= 7 THEN 'Loyal Customers'
        WHEN (r_score + f_score + m_score) >= 5 THEN 'At Risk / Need Attention'
        ELSE 'Lost / Hibernating'
    END AS customer_rfm_segment
FROM rfm_raw_scores
ORDER BY monetary_value DESC;
