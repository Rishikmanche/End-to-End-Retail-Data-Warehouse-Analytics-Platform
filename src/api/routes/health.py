"""Health check route for the FastAPI service.

Verifies database connectivity and service availability.
"""

from __future__ import annotations

import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.config import get_settings
from src.database.database import get_db, health_check
from src.schemas.schemas import HealthResponse

router = APIRouter(tags=["System health"])


@router.get("/health", response_model=HealthResponse)
def get_health_status(db: Session = Depends(get_db)) -> HealthResponse:
    """Verifies that the API service is online and the database connection is healthy."""
    db_health = health_check()
    settings = get_settings()
    
    status = "healthy"
    if db_health["status"] != "healthy":
        status = "degraded"

    return HealthResponse(
        status=status,
        db_status=db_health["status"],
        timestamp=datetime.datetime.utcnow(),
        version="1.0.0",
        environment=settings.ENVIRONMENT
    )
