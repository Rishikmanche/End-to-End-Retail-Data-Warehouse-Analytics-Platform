"""Warehouse Manager module.

Manages DDL, indexes, materialized view lifecycle, partitioning checks,
table statistics, vacuuming, and general database optimization operations.
"""

from __future__ import annotations

from typing import Any
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.models.base import Base
from src.utils.logger import get_logger

logger = get_logger(__name__)


class WarehouseManager:
    """Manages structural schema and optimization operations in the retail data warehouse."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.logger = logger

    def create_schema(self) -> None:
        """Creates all physical tables defined in the SQLAlchemy models."""
        self.logger.info("Issuing CREATE TABLE statements for all registered warehouse models...")
        Base.metadata.create_all(bind=self.engine)
        self.logger.info("Physical database schema initialization complete.")

    def drop_schema(self) -> None:
        """Drops all physical tables defined in SQLAlchemy models. WARNING: Destructive operation."""
        self.logger.warning("DROPPING all physical tables in the warehouse...")
        Base.metadata.drop_all(bind=self.engine)
        self.logger.info("Physical database schema drop complete.")

    def create_materialized_views(self) -> None:
        """Creates performance-optimized materialized views for reporting/Power BI."""
        self.logger.info("Creating materialized views...")
        
        mv_definitions = {
            "mv_monthly_sales": """
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
            "mv_customer_summary": """
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
            "mv_product_performance": """
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
        }

        with self.engine.connect() as conn:
            for mv_name, query in mv_definitions.items():
                self.logger.info("Creating materialized view: %s", mv_name)
                conn.execute(text(query))
            conn.commit()
            
        self.logger.info("Finished creating all materialized views.")

    def refresh_materialized_views(self, concurrently: bool = False) -> None:
        """Refreshes all materialized views to update cached analytical data."""
        self.logger.info("Refreshing materialized views (concurrently=%s)...", concurrently)
        views = ["mv_monthly_sales", "mv_customer_summary", "mv_product_performance"]
        
        with self.engine.connect() as conn:
            for view in views:
                try:
                    # Concurrently requires a unique index on the view
                    stmt = f"REFRESH MATERIALIZED VIEW {'CONCURRENTLY' if concurrently else ''} {view};"
                    conn.execute(text(stmt))
                    self.logger.info("Successfully refreshed %s.", view)
                except Exception as exc:
                    self.logger.error("Error refreshing materialized view %s: %s. Retrying without CONCURRENTLY.", view, exc)
                    if concurrently:
                        try:
                            conn.execute(text(f"REFRESH MATERIALIZED VIEW {view};"))
                            self.logger.info("Successfully refreshed %s sequentially.", view)
                        except Exception as sequential_exc:
                            self.logger.error("Sequential refresh failed for %s: %s", view, sequential_exc)
            conn.commit()

    def get_table_stats(self) -> dict[str, int]:
        """Queries the database to retrieve actual row counts for all tables."""
        stats = {}
        tables = ["dim_customer", "dim_product", "dim_region", "dim_date", "dim_category", "fact_sales"]
        
        with self.engine.connect() as conn:
            for t in tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {t};")).scalar()
                    stats[t] = int(result) if result is not None else 0
                except Exception as exc:
                    self.logger.warning("Could not query row count for table %s: %s", t, exc)
                    stats[t] = -1
        return stats

    def vacuum_analyze(self) -> None:
        """Executes a VACUUM ANALYZE statement on all tables to release space and rebuild query planner stats."""
        self.logger.info("Running VACUUM ANALYZE to optimize PostgreSQL query engine statistics...")
        
        # VACUUM cannot run within a transaction block in PostgreSQL
        # We need to run it on raw connection with autocommit active
        raw_conn = self.engine.raw_connection()
        try:
            raw_conn.set_isolation_level(0)  # autocommit mode
            with raw_conn.cursor() as cursor:
                cursor.execute("VACUUM ANALYZE;")
            self.logger.info("VACUUM ANALYZE completed successfully.")
        except Exception as exc:
            self.logger.error("Failed to run VACUUM ANALYZE: %s", exc)
        finally:
            raw_conn.close()

    def get_warehouse_health(self) -> dict[str, Any]:
        """Gathers table statistics, index sizing, and dead tuple information for warehouse diagnostics."""
        health = {}
        health["row_counts"] = self.get_table_stats()
        
        index_size_query = """
            SELECT
                relname AS table_name,
                pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
                pg_size_pretty(pg_relation_size(relid)) AS table_size,
                pg_size_pretty(pg_indexes_size(relid)) AS index_size
            FROM pg_catalog.pg_statio_user_tables
            ORDER BY pg_total_relation_size(relid) DESC;
        """
        
        dead_tuple_query = """
            SELECT 
                schemaname, 
                relname AS table_name, 
                n_dead_tup, 
                n_live_tup,
                ROUND(100.0 * n_dead_tup / NULLIF(n_dead_tup + n_live_tup, 0),2) as dead_tuple_ratio
            FROM pg_stat_user_tables;
        """
        
        with self.engine.connect() as conn:
            try:
                sizes = conn.execute(text(index_size_query)).fetchall()
                health["table_sizes"] = [
                    {"table": r[0], "total": r[1], "table_only": r[2], "indexes": r[3]}
                    for r in sizes
                ]
            except Exception as exc:
                self.logger.warning("Could not gather database size metrics: %s", exc)
                health["table_sizes"] = []

            try:
                tuples = conn.execute(text(dead_tuple_query)).fetchall()
                health["dead_tuples"] = [
                    {"schema": r[0], "table": r[1], "dead": r[2], "live": r[3], "ratio": r[4]}
                    for r in tuples
                ]
            except Exception as exc:
                self.logger.warning("Could not gather dead tuple metrics: %s", exc)
                health["dead_tuples"] = []
                
        return health
