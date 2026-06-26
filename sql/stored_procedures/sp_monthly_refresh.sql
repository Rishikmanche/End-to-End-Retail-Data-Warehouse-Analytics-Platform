-- ============================================================================
-- STORED FUNCTION: sp_monthly_refresh
-- ============================================================================

CREATE OR REPLACE FUNCTION sp_monthly_refresh(
    p_year INTEGER,
    p_month INTEGER
)
RETURNS TABLE (
    metric_name VARCHAR(100),
    metric_value NUMERIC
) AS $$
DECLARE
    v_sales NUMERIC;
    v_profit NUMERIC;
    v_orders INTEGER;
    v_month_key_start INTEGER;
    v_month_key_end INTEGER;
BEGIN
    RAISE INFO 'Starting monthly refresh procedure for Year: %, Month: %', p_year, p_month;
    
    -- 1. Refresh Materialized Views (updates cached reporting views)
    RAISE INFO 'Refreshing materialized views...';
    REFRESH MATERIALIZED VIEW mv_monthly_sales;
    REFRESH MATERIALIZED VIEW mv_customer_summary;
    REFRESH MATERIALIZED VIEW mv_product_performance;
    RAISE INFO 'Materialized views refreshed.';

    -- Calculate date keys for range boundary
    v_month_key_start := p_year * 10000 + p_month * 100 + 1;
    v_month_key_end := p_year * 10000 + p_month * 100 + 31;

    -- 2. Calculate summary statistics for the specified month
    SELECT 
        COALESCE(SUM(revenue), 0),
        COALESCE(SUM(profit), 0),
        COALESCE(COUNT(DISTINCT order_id), 0)
    INTO 
        v_sales,
        v_profit,
        v_orders
    FROM fact_sales
    WHERE order_date_key >= v_month_key_start AND order_date_key <= v_month_key_end;

    -- 3. Return summary metrics
    metric_name := 'Monthly Revenue';
    metric_value := v_sales;
    RETURN NEXT;

    metric_name := 'Monthly Profit';
    metric_value := v_profit;
    RETURN NEXT;

    metric_name := 'Monthly Orders';
    metric_value := v_orders::NUMERIC;
    RETURN NEXT;

    metric_name := 'Average Order Value';
    IF v_orders > 0 THEN
        metric_value := ROUND(v_sales / v_orders, 2);
    ELSE
        metric_value := 0.00;
    END IF;
    RETURN NEXT;

    RAISE INFO 'Monthly refresh procedure completed successfully.';
END;
$$ LANGUAGE plpgsql;
