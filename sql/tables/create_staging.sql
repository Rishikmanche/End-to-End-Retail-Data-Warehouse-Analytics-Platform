-- ============================================================================
-- RETAIL DATA WAREHOUSE DDL: STAGING TABLES
-- ============================================================================

-- Raw staging table (matches source CSV columns)
CREATE TABLE IF NOT EXISTS stg_raw_sales (
    row_id VARCHAR(50),
    order_id VARCHAR(50),
    order_date VARCHAR(50),
    ship_date VARCHAR(50),
    ship_mode VARCHAR(50),
    customer_id VARCHAR(50),
    customer_name VARCHAR(200),
    segment VARCHAR(50),
    country VARCHAR(100),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(50),
    region VARCHAR(50),
    product_id VARCHAR(50),
    category VARCHAR(100),
    sub_category VARCHAR(100),
    product_name VARCHAR(500),
    sales VARCHAR(50),
    quantity VARCHAR(50),
    discount VARCHAR(50),
    profit VARCHAR(50)
);

COMMENT ON TABLE stg_raw_sales IS 'Temporary raw staging table for bulk copy operations from CSV files.';

-- Clean staging table (post type-coercion, whitespace trimming, and duplicate handling)
CREATE TABLE IF NOT EXISTS stg_clean_sales (
    row_id INT,
    order_id VARCHAR(50),
    order_date TIMESTAMP,
    ship_date TIMESTAMP,
    ship_mode VARCHAR(50),
    customer_id VARCHAR(50),
    customer_name VARCHAR(200),
    segment VARCHAR(50),
    country VARCHAR(100),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    region VARCHAR(50),
    product_id VARCHAR(50),
    category VARCHAR(100),
    sub_category VARCHAR(100),
    product_name VARCHAR(500),
    sales NUMERIC(12, 2),
    quantity INT,
    discount NUMERIC(5, 2),
    profit NUMERIC(12, 2),
    revenue NUMERIC(12, 2),
    profit_margin NUMERIC(5, 4)
);

COMMENT ON TABLE stg_clean_sales IS 'Staging table for validated and cleaned data ready for dimension/fact load.';
