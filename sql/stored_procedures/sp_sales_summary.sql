-- ============================================================================
-- STORED FUNCTION: sp_sales_summary
-- ============================================================================

CREATE OR REPLACE FUNCTION sp_sales_summary(
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL,
    p_region VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    total_revenue NUMERIC,
    total_profit NUMERIC,
    total_orders BIGINT,
    total_customers BIGINT,
    total_units_sold BIGINT,
    avg_order_value NUMERIC,
    profit_margin NUMERIC
) AS $$
DECLARE
    v_start_key INTEGER := 0;
    v_end_key INTEGER := 99999999;
BEGIN
    -- Resolve date keys if dates are provided
    IF p_start_date IS NOT NULL THEN
        v_start_key := CAST(TO_CHAR(p_start_date, 'YYYYMMDD') AS INTEGER);
    END IF;
    
    IF p_end_date IS NOT NULL THEN
        v_end_key := CAST(TO_CHAR(p_end_date, 'YYYYMMDD') AS INTEGER);
    END IF;

    RETURN QUERY
    SELECT 
        COALESCE(SUM(f.revenue), 0.00) AS total_revenue,
        COALESCE(SUM(f.profit), 0.00) AS total_profit,
        COUNT(DISTINCT f.order_id) AS total_orders,
        COUNT(DISTINCT f.customer_key) AS total_customers,
        COALESCE(SUM(f.quantity)::BIGINT, 0::BIGINT) AS total_units_sold,
        ROUND(COALESCE(SUM(f.revenue), 0.00) / NULLIF(COUNT(DISTINCT f.order_id), 0), 2) AS avg_order_value,
        ROUND(COALESCE(SUM(f.profit), 0.00) / NULLIF(SUM(f.revenue), 0.00), 4) AS profit_margin
    FROM fact_sales f
    JOIN dim_region r ON f.region_key = r.region_key
    WHERE f.order_date_key >= v_start_key 
      AND f.order_date_key <= v_end_key
      AND (p_region IS NULL OR r.region = p_region);
END;
$$ LANGUAGE plpgsql;
