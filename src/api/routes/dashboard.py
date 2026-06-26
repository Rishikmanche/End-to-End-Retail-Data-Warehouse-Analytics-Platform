"""Dashboard API route.

Exposes a composite endpoint aggregating KPIs and charts for dashboard visualization.
"""

from __future__ import annotations

from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.analytics.queries import AnalyticsEngine
from src.database.database import get_db
from src.schemas.schemas import DashboardResponse, KPIResponse

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard-data", response_model=DashboardResponse)
def get_dashboard_payload(db: Session = Depends(get_db)) -> DashboardResponse:
    """Retrieves composite dashboard payload containing KPIs and summary chart data."""
    engine_inst = db.get_bind()
    analytics = AnalyticsEngine(engine_inst)
    
    # 1. Fetch KPIs
    kpi_dict = analytics.get_kpis()
    kpis = KPIResponse(
        total_sales=kpi_dict["net_revenue"],
        total_profit=kpi_dict["total_profit"],
        total_orders=kpi_dict["total_orders"],
        avg_order_value=kpi_dict["average_order_value"],
        profit_margin=kpi_dict["net_profit_margin"],
        total_customers=kpi_dict["total_customers"]
    )
    
    # 2. Fetch sales by category
    cat_df = analytics.profitability_analysis(by="category")
    # Group by category_name in dataframe to resolve duplicate ship mode rows
    cat_summary = cat_df.groupby("category_name").agg({
        "total_revenue": "sum",
        "total_profit": "sum"
    }).reset_index()
    sales_by_category = [
        {
            "category": row["category_name"],
            "sales": float(row["total_revenue"]),
            "profit": float(row["total_profit"])
        }
        for _, row in cat_summary.iterrows()
    ]

    # 3. Fetch sales by region
    reg_df = analytics.regional_performance()
    reg_summary = reg_df.groupby("region").agg({
        "total_revenue": "sum",
        "total_profit": "sum"
    }).reset_index()
    sales_by_region = [
        {
            "region": row["region"],
            "sales": float(row["total_revenue"]),
            "profit": float(row["total_profit"])
        }
        for _, row in reg_summary.iterrows()
    ]

    # 4. Fetch monthly trends
    trend_df = analytics.sales_trends(granularity="monthly")
    monthly_trend = [
        {
            "year": int(row["year"]),
            "month": int(row["month"]),
            "month_name": row["month_name"],
            "sales": float(row["total_revenue"]),
            "profit": float(row["total_profit"]),
            "orders": int(row["total_orders"])
        }
        for _, row in trend_df.iterrows()
    ]

    # 5. Fetch top products
    prod_df = analytics.top_products(limit=5)
    top_products = [
        {
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "category": row["category_name"],
            "sales": float(row["total_revenue"]),
            "profit": float(row["total_profit"])
        }
        for _, row in prod_df.iterrows()
    ]

    return DashboardResponse(
        kpis=kpis,
        sales_by_category=sales_by_category,
        sales_by_region=sales_by_region,
        monthly_trend=monthly_trend,
        top_products=top_products
    )
