"""Analytics query engine for the Retail Data Warehouse.

Provides parameterized analytical queries returning pandas DataFrames for
easy consumption by the API, reporting views, and Jupyter notebooks.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.utils.logger import get_logger

logger = get_logger(__name__)


class AnalyticsEngine:
    """Executes high-performance analytical queries against the Postgres star schema."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.logger = logger

    def revenue_by_month(self, year: int | None = None) -> pd.DataFrame:
        """Calculates monthly sales revenue and gross profit metrics.

        Args:
            year: Optional calendar year to filter.

        Returns:
            A pandas DataFrame with monthly aggregates.
        """
        self.logger.debug("Executing revenue_by_month query. Year filter: %s", year)
        query = """
            SELECT 
                d.year,
                d.month,
                d.month_name,
                SUM(f.sales) AS total_sales,
                SUM(f.revenue) AS total_revenue,
                SUM(f.profit) AS total_profit,
                SUM(f.quantity) AS total_quantity,
                COUNT(DISTINCT f.order_id) AS total_orders,
                ROUND(SUM(f.revenue) * 1.0 / NULLIF(COUNT(DISTINCT f.order_id), 0), 2) AS average_order_value,
                ROUND(SUM(f.profit) * 1.0 / NULLIF(SUM(f.revenue), 0), 4) AS profit_margin
            FROM fact_sales f
            JOIN dim_date d ON f.order_date_key = d.date_key
            {where_clause}
            GROUP BY d.year, d.month, d.month_name
            ORDER BY d.year, d.month;
        """
        
        where_clause = ""
        params = {}
        if year:
            where_clause = "WHERE d.year = :year"
            params["year"] = year

        formatted_query = query.format(where_clause=where_clause)
        
        with self.engine.connect() as conn:
            df = pd.read_sql_query(text(formatted_query), conn, params=params)
            
        return df

    def top_customers(self, limit: int = 10) -> pd.DataFrame:
        """Retrieves top customers ordered by total revenue and calculates average margins."""
        self.logger.debug("Executing top_customers query. Limit: %d", limit)
        query = """
            SELECT 
                c.customer_id,
                c.customer_name,
                c.segment,
                SUM(f.sales) AS total_sales,
                SUM(f.revenue) AS total_revenue,
                SUM(f.profit) AS total_profit,
                COUNT(DISTINCT f.order_id) AS total_orders,
                ROUND(SUM(f.profit) * 1.0 / NULLIF(SUM(f.revenue), 0), 4) AS profit_margin
            FROM fact_sales f
            JOIN dim_customer c ON f.customer_key = c.customer_key
            GROUP BY c.customer_id, c.customer_name, c.segment
            ORDER BY total_revenue DESC
            LIMIT :limit;
        """
        with self.engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn, params={"limit": limit})
        return df

    def top_products(self, limit: int = 10, category: str | None = None) -> pd.DataFrame:
        """Retrieves best-performing products by total revenue."""
        self.logger.debug("Executing top_products query. Limit: %d, Category: %s", limit, category)
        query = """
            SELECT 
                p.product_id,
                p.product_name,
                cat.category_name,
                p.sub_category,
                SUM(f.sales) AS total_sales,
                SUM(f.revenue) AS total_revenue,
                SUM(f.profit) AS total_profit,
                SUM(f.quantity) AS total_quantity,
                ROUND(AVG(f.discount), 4) AS average_discount
            FROM fact_sales f
            JOIN dim_product p ON f.product_key = p.product_key
            JOIN dim_category cat ON f.category_key = cat.category_key
            {where_clause}
            GROUP BY p.product_id, p.product_name, cat.category_name, p.sub_category
            ORDER BY total_revenue DESC
            LIMIT :limit;
        """
        where_clause = ""
        params = {"limit": limit}
        if category:
            where_clause = "WHERE cat.category_name = :category"
            params["category"] = category
            
        formatted_query = query.format(where_clause=where_clause)
        
        with self.engine.connect() as conn:
            df = pd.read_sql_query(text(formatted_query), conn, params=params)
        return df

    def regional_performance(self) -> pd.DataFrame:
        """Calculates sales and profit breakdown across regions and states."""
        query = """
            SELECT 
                r.region,
                r.country,
                r.state,
                SUM(f.sales) AS total_sales,
                SUM(f.revenue) AS total_revenue,
                SUM(f.profit) AS total_profit,
                COUNT(DISTINCT f.order_id) AS total_orders,
                ROUND(SUM(f.profit) / NULLIF(SUM(f.revenue), 0), 4) AS profit_margin
            FROM fact_sales f
            JOIN dim_region r ON f.region_key = r.region_key
            GROUP BY r.region, r.country, r.state
            ORDER BY r.region, total_revenue DESC;
        """
        with self.engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn)
        return df

    def sales_trends(self, granularity: str = "monthly") -> pd.DataFrame:
        """Gathers aggregate sales trend lines at various date granularities."""
        self.logger.debug("Executing sales_trends. Granularity: %s", granularity)
        
        if granularity == "daily":
            group_cols = "d.full_date"
            order_cols = "d.full_date"
        elif granularity == "weekly":
            group_cols = "d.year, d.week_of_year"
            order_cols = "d.year, d.week_of_year"
        elif granularity == "quarterly":
            group_cols = "d.year, d.quarter"
            order_cols = "d.year, d.quarter"
        else:  # default monthly
            group_cols = "d.year, d.month, d.month_name"
            order_cols = "d.year, d.month"

        query = f"""
            SELECT 
                {group_cols},
                SUM(f.sales) AS total_sales,
                SUM(f.revenue) AS total_revenue,
                SUM(f.profit) AS total_profit,
                COUNT(DISTINCT f.order_id) AS total_orders
            FROM fact_sales f
            JOIN dim_date d ON f.order_date_key = d.date_key
            GROUP BY {group_cols}
            ORDER BY {order_cols};
        """
        with self.engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn)
        return df

    def customer_segmentation(self) -> pd.DataFrame:
        """Performs RFM (Recency, Frequency, Monetary) Customer Segmentation analysis."""
        self.logger.debug("Executing RFM customer segmentation...")
        # Since date logic defaults to current time, recency is difference between last transaction
        # date and max order date in the dataset.
        query = """
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
            rfm_scores AS (
                SELECT 
                    m.*,
                    (SELECT max_date FROM reference_date) - m.last_order_date AS recency_days,
                    NTILE(4) OVER (ORDER BY (SELECT max_date FROM reference_date) - m.last_order_date DESC) AS r_score, -- higher is more recent (lower days)
                    NTILE(4) OVER (ORDER BY m.order_frequency ASC) AS f_score, -- higher is more frequent
                    NTILE(4) OVER (ORDER BY m.monetary_value ASC) AS m_score -- higher spends more
                FROM customer_metrics m
            )
            SELECT 
                r.customer_id,
                r.customer_name,
                r.market_segment,
                r.last_order_date,
                r.recency_days,
                r.order_frequency,
                r.monetary_value,
                (r.r_score + r.f_score + r.m_score) AS rfm_total_score,
                CASE 
                    WHEN (r.r_score + r.f_score + r.m_score) >= 10 THEN 'Champions'
                    WHEN (r.r_score + r.f_score + r.m_score) >= 7 THEN 'Loyal Customers'
                    WHEN (r.r_score + r.f_score + r.m_score) >= 5 THEN 'At Risk / Need Attention'
                    ELSE 'Lost / Hibernating'
                END AS customer_rfm_segment
            FROM rfm_scores r
            ORDER BY monetary_value DESC;
        """
        with self.engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn)
        return df

    def profitability_analysis(self, by: str = "category") -> pd.DataFrame:
        """Analyzes profitability by dimensions (category, product, region, or segment)."""
        self.logger.debug("Executing profitability_analysis by: %s", by)
        
        if by == "product":
            select_cols = "p.product_id, p.product_name, cat.category_name, p.sub_category"
            join_clause = """
                JOIN dim_product p ON f.product_key = p.product_key
                JOIN dim_category cat ON f.category_key = cat.category_key
            """
            group_cols = "p.product_id, p.product_name, cat.category_name, p.sub_category"
        elif by == "region":
            select_cols = "r.region, r.state, r.city"
            join_clause = "JOIN dim_region r ON f.region_key = r.region_key"
            group_cols = "r.region, r.state, r.city"
        elif by == "customer":
            select_cols = "c.customer_id, c.customer_name, c.segment"
            join_clause = "JOIN dim_customer c ON f.customer_key = c.customer_key"
            group_cols = "c.customer_id, c.customer_name, c.segment"
        else:  # default category
            select_cols = "cat.category_name, f.ship_mode"
            join_clause = "JOIN dim_category cat ON f.category_key = cat.category_key"
            group_cols = "cat.category_name, f.ship_mode"

        query = f"""
            SELECT 
                {select_cols},
                SUM(f.sales) AS total_sales,
                SUM(f.revenue) AS total_revenue,
                SUM(f.profit) AS total_profit,
                ROUND(SUM(f.profit) * 1.0 / NULLIF(SUM(f.revenue), 0), 4) AS profit_margin
            FROM fact_sales f
            {join_clause}
            GROUP BY {group_cols}
            ORDER BY total_revenue DESC;
        """
        with self.engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn)
        return df

    def get_kpis(self) -> dict[str, float]:
        """Calculates core high-level KPIs for executive dashboards."""
        self.logger.debug("Executing get_kpis query...")
        query = """
            SELECT 
                SUM(sales) as gross_sales,
                SUM(revenue) as net_revenue,
                SUM(profit) as total_profit,
                SUM(quantity) as total_quantity,
                COUNT(DISTINCT order_id) as total_orders,
                COUNT(DISTINCT customer_key) as total_customers,
                ROUND(SUM(revenue) * 1.0 / NULLIF(COUNT(DISTINCT order_id), 0), 2) as average_order_value,
                ROUND(SUM(profit) * 1.0 / NULLIF(SUM(revenue), 0), 4) as net_profit_margin
            FROM fact_sales;
        """
        
        with self.engine.connect() as conn:
            result = conn.execute(text(query)).fetchone()
            
        if not result or result[0] is None:
            return {
                "gross_sales": 0.0,
                "net_revenue": 0.0,
                "total_profit": 0.0,
                "total_quantity": 0,
                "total_orders": 0,
                "total_customers": 0,
                "average_order_value": 0.0,
                "net_profit_margin": 0.0,
            }
            
        return {
            "gross_sales": float(result[0]),
            "net_revenue": float(result[1]),
            "total_profit": float(result[2]),
            "total_quantity": int(result[3]),
            "total_orders": int(result[4]),
            "total_customers": int(result[5]),
            "average_order_value": float(result[6]),
            "net_profit_margin": float(result[7]),
        }

    def discount_impact(self) -> pd.DataFrame:
        """Analyzes how different discount levels impact total volume and profit margins."""
        query = """
            SELECT 
                discount AS discount_rate,
                COUNT(*) AS transaction_count,
                SUM(sales) AS total_sales,
                SUM(revenue) AS total_revenue,
                SUM(profit) AS total_profit,
                ROUND(SUM(profit) / NULLIF(SUM(revenue), 0), 4) AS profit_margin,
                SUM(quantity) AS total_units_sold
            FROM fact_sales
            GROUP BY discount
            ORDER BY discount;
        """
        with self.engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn)
        return df

    def monthly_growth(self) -> pd.DataFrame:
        """Calculates Month-over-Month (MoM) revenue growth trends."""
        query = """
            WITH monthly_sales AS (
                SELECT 
                    d.year,
                    d.month,
                    d.month_name,
                    SUM(f.revenue) AS monthly_revenue
                FROM fact_sales f
                JOIN dim_date d ON f.order_date_key = d.date_key
                GROUP BY d.year, d.month, d.month_name
            )
            SELECT 
                year,
                month,
                month_name,
                monthly_revenue,
                LAG(monthly_revenue) OVER (ORDER BY year, month) AS prior_month_revenue,
                ROUND(
                    (monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY year, month)) 
                    / NULLIF(LAG(monthly_revenue) OVER (ORDER BY year, month), 0) * 100.0, 
                    2
                ) AS mom_growth_pct
            FROM monthly_sales
            ORDER BY year, month;
        """
        with self.engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn)
        return df
