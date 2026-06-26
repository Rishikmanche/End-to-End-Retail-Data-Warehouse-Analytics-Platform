-- ============================================================================
-- RETAIL DATA WAREHOUSE DDL: DIMENSION TABLES
-- ============================================================================

-- 1. Date Dimension Table
CREATE TABLE IF NOT EXISTS dim_date (
    date_key INT PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    day_of_week INT NOT NULL,
    day_name VARCHAR(10) NOT NULL,
    day_of_month INT NOT NULL,
    day_of_year INT NOT NULL,
    week_of_year INT NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(10) NOT NULL,
    quarter INT NOT NULL,
    year INT NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    is_holiday BOOLEAN NOT NULL,
    fiscal_quarter INT NOT NULL,
    fiscal_year INT NOT NULL
);

COMMENT ON TABLE dim_date IS 'Time dimension mapping dates (Order & Ship Dates) to calendar & fiscal periods.';
COMMENT ON COLUMN dim_date.date_key IS 'Surrogate key formatted as YYYYMMDD.';
COMMENT ON COLUMN dim_date.full_date IS 'Actual date value.';

-- 2. Category Dimension Table
CREATE TABLE IF NOT EXISTS dim_category (
    category_key SERIAL PRIMARY KEY,
    category_id VARCHAR(50) NOT NULL UNIQUE,
    category_name VARCHAR(100) NOT NULL,
    sub_category VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE dim_category IS 'Product category hierarchical groupings.';
COMMENT ON COLUMN dim_category.category_id IS 'Unique text code generated for Category-SubCategory.';

-- 3. Product Dimension Table
CREATE TABLE IF NOT EXISTS dim_product (
    product_key SERIAL PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL UNIQUE,
    product_name VARCHAR(500) NOT NULL,
    category_key INT REFERENCES dim_category(category_key),
    sub_category VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE dim_product IS 'Individual product catalog dimension table.';
COMMENT ON COLUMN dim_product.product_id IS 'Natural product code.';

-- 4. Region Dimension Table
CREATE TABLE IF NOT EXISTS dim_region (
    region_key SERIAL PRIMARY KEY,
    country VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    state VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dim_region UNIQUE (country, state, city, postal_code)
);

COMMENT ON TABLE dim_region IS 'Geography dimension mapping transaction locations.';

-- 5. Customer Dimension Table (SCD Type 2)
CREATE TABLE IF NOT EXISTS dim_customer (
    customer_key SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    customer_name VARCHAR(200) NOT NULL,
    segment VARCHAR(50),
    effective_date DATE NOT NULL,
    expiry_date DATE,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE dim_customer IS 'Customer history profile dimension table supporting SCD Type 2 changes.';
COMMENT ON COLUMN dim_customer.customer_id IS 'Natural stable customer ID.';
COMMENT ON COLUMN dim_customer.effective_date IS 'SCD Type 2 version start date.';
COMMENT ON COLUMN dim_customer.expiry_date IS 'SCD Type 2 version end date (NULL if current active record).';
