-- ============================================================================
-- RETAIL DATA WAREHOUSE INDEX OPTIMIZATION INDEXES
-- ============================================================================

-- 1. B-tree Indexes on Foreign Keys in Fact Table
-- Speeds up joins between fact and dimension tables.
CREATE INDEX IF NOT EXISTS ix_fact_sales_order_date_key ON fact_sales(order_date_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_ship_date_key ON fact_sales(ship_date_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_customer_key ON fact_sales(customer_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_product_key ON fact_sales(product_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_region_key ON fact_sales(region_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_category_key ON fact_sales(category_key);

-- 2. Composite Indexes
-- Speeds up aggregations filtering on order_date_key and customer_key simultaneously
CREATE INDEX IF NOT EXISTS ix_fact_sales_date_customer ON fact_sales(order_date_key, customer_key);

-- Speeds up joins and filtering on product and category attributes
CREATE INDEX IF NOT EXISTS ix_fact_sales_product_category ON fact_sales(product_key, category_key);

-- 3. Partial Indexes (PostgreSQL Specific Optimization)
-- Indexes only loss-making transactions. Excellent for discount impact and alert audits.
CREATE INDEX IF NOT EXISTS ix_fact_sales_loss_making 
ON fact_sales(sales_key, profit) 
WHERE profit < 0;

-- Indexes segment on active customer profiles (SCD Type 2 optimization)
CREATE INDEX IF NOT EXISTS ix_dim_customer_active_segment 
ON dim_customer(customer_id, segment) 
WHERE is_current = TRUE;

-- 4. Multi-column Index on Time Dimensions
CREATE INDEX IF NOT EXISTS ix_dim_date_calendar 
ON dim_date(year, quarter, month, date_key);

-- ============================================================================
-- PERFORMANCE & EXPLAIN PLAN DOCUMENTATION:
-- ============================================================================
/*
1. Querying loss-making products:
   EXPLAIN ANALYZE
   SELECT product_key, SUM(profit)
   FROM fact_sales
   WHERE profit < 0
   GROUP BY product_key;
   
   Expected Optimization:
   Without the Partial Index 'ix_fact_sales_loss_making', the database engine performs
   a Sequential Scan over the entire 'fact_sales' table (Cost ~ O(N) where N is row count).
   With 'ix_fact_sales_loss_making', the query planner performs an Index Scan (Cost ~ O(M) 
   where M is the count of negative profit records, typically M << N), leading to a 90%+
   reduction in buffer reads.

2. SCD Type 2 Active Customer filters:
   EXPLAIN ANALYZE
   SELECT customer_name, segment
   FROM dim_customer
   WHERE is_current = TRUE AND segment = 'Consumer';

   Expected Optimization:
   Uses 'ix_dim_customer_active_segment' to directly locate current records matching 'Consumer'
   avoiding scanning expired historical records.
*/
