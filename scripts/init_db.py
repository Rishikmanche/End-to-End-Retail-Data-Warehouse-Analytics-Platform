"""Database initialization script.

Applies dimension, fact, staging tables DDL, indexes, analytical views,
and stored functions/procedures against PostgreSQL.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from sqlalchemy import text

from src.config.config import get_settings
from src.database.database import engine
from src.utils.logger import get_logger

logger = get_logger(__name__)


def execute_sql_file(conn, filepath: Path) -> None:
    """Reads a SQL file and executes it. Splits by semicolon unless it contains a function definition."""
    logger.info("Executing SQL script: %s", filepath.name)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    import re
    # Check if it is a stored procedure/function definition
    if "$$" in content or "CREATE OR REPLACE FUNCTION" in content or "CREATE FUNCTION" in content:
        conn.execute(text(content))
    else:
        # Remove block comments (/* ... */)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # Remove line comments (-- ...)
        content = re.sub(r'--.*$', '', content, flags=re.MULTILINE)
        
        statements = content.split(";")
        for statement in statements:
            trimmed = statement.strip()
            if trimmed:
                conn.execute(text(trimmed))


def init_database(drop_existing: bool = False) -> None:
    """Executes SQL scripts in order to create schemas, indexes, views, and functions."""
    sql_base_dir = Path("sql")
    
    # Ordering of executions is critical due to PK/FK dependencies
    staging_ddl = sql_base_dir / "tables" / "create_staging.sql"
    dim_ddl = sql_base_dir / "tables" / "create_dimensions.sql"
    fact_ddl = sql_base_dir / "tables" / "create_facts.sql"
    indexes_ddl = sql_base_dir / "indexes" / "create_indexes.sql"
    
    views_dir = sql_base_dir / "views"
    procedures_dir = sql_base_dir / "stored_procedures"

    # Gather all views
    view_files = list(views_dir.glob("*.sql"))
    # Gather all procedures
    procedure_files = list(procedures_dir.glob("*.sql"))

    with engine.begin() as conn:
        if drop_existing:
            logger.warning("Dropping existing tables and views...")
            conn.execute(text("DROP TABLE IF EXISTS fact_sales CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS dim_customer CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS dim_product CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS dim_region CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS dim_date CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS dim_category CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS stg_raw_sales CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS stg_clean_sales CASCADE;"))
            logger.info("Drop complete.")

        # 1. Create Staging Tables
        if staging_ddl.exists():
            execute_sql_file(conn, staging_ddl)
            
        # 2. Create Dimensions
        if dim_ddl.exists():
            execute_sql_file(conn, dim_ddl)
            
        # 3. Create Facts (and child partitions)
        if fact_ddl.exists():
            execute_sql_file(conn, fact_ddl)

        # 4. Create Indexes
        if indexes_ddl.exists():
            execute_sql_file(conn, indexes_ddl)

        # 5. Create Materialized Views (creates mv_* views)
        # We also have analytical views inside sql/views/
        logger.info("Creating analytical views...")
        for vf in view_files:
            execute_sql_file(conn, vf)

        # 6. Create Stored Procedures
        logger.info("Creating stored procedures...")
        for pf in procedure_files:
            execute_sql_file(conn, pf)

        # 7. Create Materialized Views from Python Manager (if applicable, done inline)
        logger.info("Creating materialized views...")
        mv_queries = [
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_monthly_sales AS
            SELECT 
                d.year,
                d.month,
                d.month_name,
                c.category_name,
                SUM(f.sales) as total_sales,
                SUM(f.revenue) as total_revenue,
                SUM(f.profit) as total_profit,
                SUM(f.quantity) as total_quantity,
                COUNT(DISTINCT f.order_id) as total_orders
            FROM fact_sales f
            JOIN dim_date d ON f.order_date_key = d.date_key
            JOIN dim_category c ON f.category_key = c.category_key
            GROUP BY d.year, d.month, d.month_name, c.category_name
            WITH DATA;
            """,
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_customer_summary AS
            SELECT 
                c.customer_key,
                c.customer_id,
                c.customer_name,
                c.segment,
                SUM(f.sales) as lifetime_sales,
                SUM(f.revenue) as lifetime_revenue,
                SUM(f.profit) as lifetime_profit,
                COUNT(DISTINCT f.order_id) as total_orders,
                MAX(d.full_date) as last_order_date
            FROM fact_sales f
            JOIN dim_customer c ON f.customer_key = c.customer_key
            JOIN dim_date d ON f.order_date_key = d.date_key
            GROUP BY c.customer_key, c.customer_id, c.customer_name, c.segment
            WITH DATA;
            """,
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_product_performance AS
            SELECT 
                p.product_key,
                p.product_id,
                p.product_name,
                c.category_name,
                p.sub_category,
                SUM(f.sales) as total_sales,
                SUM(f.revenue) as total_revenue,
                SUM(f.profit) as total_profit,
                SUM(f.quantity) as total_quantity
            FROM fact_sales f
            JOIN dim_product p ON f.product_key = p.product_key
            JOIN dim_category c ON f.category_key = c.category_key
            GROUP BY p.product_key, p.product_id, p.product_name, c.category_name, p.sub_category
            WITH DATA;
            """
        ]
        for query in mv_queries:
            conn.execute(text(query))

    logger.info("Database initialized successfully.")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Initialize retail data warehouse schema.")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing tables and views before creating new schema."
    )
    args = parser.parse_args()

    print(f"Initializing database...")
    init_database(drop_existing=args.drop)


if __name__ == "__main__":
    main()
