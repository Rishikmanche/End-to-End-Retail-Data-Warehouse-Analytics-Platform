"""Sales API route.

Exposes paginated endpoints for querying sales fact transactions.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.models.fact_sales import FactSales
from src.models.dim_customer import DimCustomer
from src.models.dim_product import DimProduct
from src.models.dim_region import DimRegion
from src.models.dim_category import DimCategory
from src.models.dim_date import DimDate
from src.schemas.schemas import SalesResponse, PaginatedResponse

router = APIRouter(tags=["Sales Transactions"])


@router.get("/sales", response_model=PaginatedResponse[SalesResponse])
def get_sales_transactions(
    start_date: datetime.date | None = Query(default=None, description="Start date filter (YYYY-MM-DD)"),
    end_date: datetime.date | None = Query(default=None, description="End date filter (YYYY-MM-DD)"),
    region: str | None = Query(default=None, description="Region filter"),
    category: str | None = Query(default=None, description="Category filter"),
    min_sales: float | None = Query(default=None, description="Minimum sales amount"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db)
) -> PaginatedResponse[SalesResponse]:
    """Retrieves paginated sales transaction list from the warehouse, supporting dynamic filters."""
    
    # Base query joining fact table with all dimensions
    OrderDate = select(DimDate.full_date).where(DimDate.date_key == FactSales.order_date_key).scalar_subquery()
    ShipDate = select(DimDate.full_date).where(DimDate.date_key == FactSales.ship_date_key).scalar_subquery()

    query = select(
        FactSales.sales_key,
        FactSales.order_id,
        FactSales.sales,
        FactSales.quantity,
        FactSales.discount,
        FactSales.profit,
        FactSales.revenue,
        FactSales.profit_margin,
        OrderDate.label("order_date"),
        ShipDate.label("ship_date"),
        DimCustomer.customer_name.label("customer_name"),
        DimProduct.product_name.label("product_name"),
        DimRegion.region.label("region"),
        DimCategory.category_name.label("category")
    ).select_from(FactSales)\
     .join(DimCustomer, FactSales.customer_key == DimCustomer.customer_key)\
     .join(DimProduct, FactSales.product_key == DimProduct.product_key)\
     .join(DimRegion, FactSales.region_key == DimRegion.region_key)\
     .join(DimCategory, FactSales.category_key == DimCategory.category_key)

    # Apply filters
    if start_date or end_date:
        # Resolve dates using date_key or direct join
        # For simplicity, filter on subquery order_date or join with order date
        query = query.join(DimDate, FactSales.order_date_key == DimDate.date_key)
        if start_date:
            query = query.where(DimDate.full_date >= start_date)
        if end_date:
            query = query.where(DimDate.full_date <= end_date)

    if region:
        query = query.where(DimRegion.region == region)
        
    if category:
        query = query.where(DimCategory.category_name == category)

    if min_sales is not None:
        query = query.where(FactSales.sales >= min_sales)

    # Get total count
    total = db.scalar(select(func.count()).select_from(query.subquery()))

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute
    results = db.execute(query).fetchall()

    items = []
    for r in results:
        items.append(SalesResponse(
            sales_key=r.sales_key,
            order_id=r.order_id,
            sales=Decimal(str(r.sales)),
            quantity=r.quantity,
            discount=Decimal(str(r.discount)),
            profit=Decimal(str(r.profit)),
            order_date=r.order_date,
            ship_date=r.ship_date,
            customer_name=r.customer_name,
            product_name=r.product_name,
            region=r.region,
            category=r.category,
            revenue=Decimal(str(r.revenue)) if r.revenue is not None else None,
            profit_margin=Decimal(str(r.profit_margin)) if r.profit_margin is not None else None
        ))

    total_pages = math.ceil(total / page_size) if total else 0

    return PaginatedResponse[SalesResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
