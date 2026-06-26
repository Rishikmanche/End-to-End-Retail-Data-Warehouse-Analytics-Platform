"""Customers API route.

Exposes paginated endpoints for customer dimensions.
"""

from __future__ import annotations

import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.models.dim_customer import DimCustomer
from src.schemas.schemas import CustomerResponse, PaginatedResponse

router = APIRouter(tags=["Customers"])


@router.get("/customers", response_model=PaginatedResponse[CustomerResponse])
def get_customers(
    segment: str | None = Query(default=None, description="Filter customers by segment"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db)
) -> PaginatedResponse[CustomerResponse]:
    """Retrieves paginated customers list from the warehouse, optionally filtered by segment."""
    # Build query
    query = select(DimCustomer).where(DimCustomer.is_current == True)
    
    if segment:
        query = query.where(DimCustomer.segment == segment)
        
    # Get total count
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    items = db.scalars(query).all()
    
    total_pages = math.ceil(total / page_size) if total else 0
    
    return PaginatedResponse[CustomerResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer_by_id(customer_id: str, db: Session = Depends(get_db)) -> CustomerResponse:
    """Retrieves the active profile details of a customer by natural customer_id."""
    stmt = select(DimCustomer).where(
        DimCustomer.customer_id == customer_id,
        DimCustomer.is_current == True
    )
    customer = db.scalar(stmt)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Active customer profile with ID '{customer_id}' not found.")
    return customer
