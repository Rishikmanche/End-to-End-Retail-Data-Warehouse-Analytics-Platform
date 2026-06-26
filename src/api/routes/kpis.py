"""KPIs API route.

Exposes aggregated sales, volume, revenue, profit, and margin KPIs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.analytics.queries import AnalyticsEngine
from src.database.database import get_db
from src.schemas.schemas import KPIResponse

router = APIRouter(tags=["Performance KPIs"])


@router.get("/kpis", response_model=KPIResponse)
def get_warehouse_kpis(db: Session = Depends(get_db)) -> KPIResponse:
    """Retrieves high-level performance KPIs from the sales transactions."""
    engine_inst = db.get_bind()
    analytics = AnalyticsEngine(engine_inst)
    kpi_dict = analytics.get_kpis()
    
    return KPIResponse(
        total_sales=kpi_dict["net_revenue"],  # Using net revenue as total sales
        total_profit=kpi_dict["total_profit"],
        total_orders=kpi_dict["total_orders"],
        avg_order_value=kpi_dict["average_order_value"],
        profit_margin=kpi_dict["net_profit_margin"],
        total_customers=kpi_dict["total_customers"]
    )
