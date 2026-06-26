-- ============================================================================
-- RETAIL DATA WAREHOUSE DDL: FACT SALES TABLE WITH PARTITIONING
-- ============================================================================

-- Create partitioned fact_sales table
CREATE TABLE IF NOT EXISTS fact_sales (
    sales_key SERIAL,
    order_id VARCHAR(50) NOT NULL,
    order_date_key INT NOT NULL REFERENCES dim_date(date_key) ON DELETE RESTRICT,
    ship_date_key INT NOT NULL REFERENCES dim_date(date_key) ON DELETE RESTRICT,
    customer_key INT NOT NULL REFERENCES dim_customer(customer_key) ON DELETE RESTRICT,
    product_key INT NOT NULL REFERENCES dim_product(product_key) ON DELETE RESTRICT,
    region_key INT NOT NULL REFERENCES dim_region(region_key) ON DELETE RESTRICT,
    category_key INT NOT NULL REFERENCES dim_category(category_key) ON DELETE RESTRICT,
    ship_mode VARCHAR(50) NOT NULL,
    sales NUMERIC(12, 2) NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    discount NUMERIC(5, 2) NOT NULL DEFAULT 0.00 CHECK (discount >= 0.00 AND discount <= 1.00),
    profit NUMERIC(12, 2) NOT NULL,
    revenue NUMERIC(12, 2) NOT NULL,
    profit_margin NUMERIC(5, 4) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (sales_key, order_date_key)
) PARTITION BY RANGE (order_date_key);

COMMENT ON TABLE fact_sales IS 'Partitioned transaction sales fact table.';
COMMENT ON COLUMN fact_sales.sales_key IS 'Surrogate transaction key.';
COMMENT ON COLUMN fact_sales.revenue IS 'Net revenue: Sales * (1 - Discount).';
COMMENT ON COLUMN fact_sales.profit_margin IS 'Net profit margin: Profit / Sales.';

-- Create annual range partitions
CREATE TABLE IF NOT EXISTS fact_sales_2021 PARTITION OF fact_sales
    FOR VALUES FROM (20210101) TO (20220101);

CREATE TABLE IF NOT EXISTS fact_sales_2022 PARTITION OF fact_sales
    FOR VALUES FROM (20220101) TO (20230101);

CREATE TABLE IF NOT EXISTS fact_sales_2023 PARTITION OF fact_sales
    FOR VALUES FROM (20230101) TO (20240101);

CREATE TABLE IF NOT EXISTS fact_sales_2024 PARTITION OF fact_sales
    FOR VALUES FROM (20240101) TO (20250101);

CREATE TABLE IF NOT EXISTS fact_sales_2025 PARTITION OF fact_sales
    FOR VALUES FROM (20250101) TO (20260101);

-- Default partition for values outside range
CREATE TABLE IF NOT EXISTS fact_sales_default PARTITION OF fact_sales DEFAULT;
