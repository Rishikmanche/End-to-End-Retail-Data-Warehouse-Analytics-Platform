"""Products API route.

Exposes paginated endpoints for product dimensions.
"""

from __future__ import annotations

import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.models.dim_product import DimProduct
from src.models.dim_category import DimCategory
from src.schemas.schemas import ProductResponse, PaginatedResponse

router = APIRouter(tags=["Products"])


@router.get("/products", response_model=PaginatedResponse[ProductResponse])
def get_products(
    category: str | None = Query(default=None, description="Filter products by category name"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db)
) -> PaginatedResponse[ProductResponse]:
    """Retrieves paginated products list from the warehouse, optionally filtered by category."""
    # Build query joining with Category to get category_name
    query = select(
        DimProduct.product_key,
        DimProduct.product_id,
        DimProduct.product_name,
        DimProduct.sub_category,
        DimCategory.category_name.label("category_name")
    ).outerjoin(DimCategory, DimProduct.category_key == DimCategory.category_key)
    
    if category:
        query = query.where(DimCategory.category_name == category)
        
    # Get total count
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    results = db.execute(query).fetchall()
    
    # Map row tuples to response dictionaries/objects
    items = []
    for r in results:
        items.append(ProductResponse(
            product_key=r.product_key,
            product_id=r.product_id,
            product_name=r.product_name,
            sub_category=r.sub_category,
            category_name=r.category_name
        ))
    
    total_pages = math.ceil(total / page_size) if total else 0
    
    return PaginatedResponse[ProductResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product_by_id(product_id: str, db: Session = Depends(get_db)) -> ProductResponse:
    """Retrieves product details by natural product_id."""
    stmt = select(
        DimProduct.product_key,
        DimProduct.product_id,
        DimProduct.product_name,
        DimProduct.sub_category,
        DimCategory.category_name.label("category_name")
    ).outerjoin(DimCategory, DimProduct.category_key == DimCategory.category_key).where(DimProduct.product_id == product_id)
    
    r = db.execute(stmt).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail=f"Product with ID '{product_id}' not found.")
        
    return ProductResponse(
        product_key=r.product_key,
        product_id=r.product_id,
        product_name=r.product_name,
        sub_category=r.sub_category,
        category_name=r.category_name
    )
