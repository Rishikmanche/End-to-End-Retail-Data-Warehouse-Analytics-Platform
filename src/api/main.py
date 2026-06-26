"""FastAPI Application Entry Point.

Configures application settings, middleware, exception handlers, lifecycle events,
and registers all entity and analytics router endpoints.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import customers, dashboard, health, kpis, products, sales
from src.config.config import get_settings
from src.database.database import engine, health_check

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and shutdown lifecycle events."""
    logger.info("Starting Retail Analytics Platform API service...")
    
    # Verify database connectivity on startup
    db_status = health_check()
    if db_status["status"] == "healthy":
        logger.info("Database connection verified successfully.")
    else:
        logger.error("Failed to connect to the database on startup: %s", db_status["error"])
        
    yield
    
    logger.info("Shutting down Retail Analytics Platform API service...")
    # Close any database connection pools if needed
    engine.dispose()
    logger.info("Database connection pools disposed.")


app = FastAPI(
    title="Retail Data Warehouse & Analytics Platform API",
    description=(
        "Production-quality REST API exposing dimensions, transactional facts, "
        "and summary KPIs from the PostgreSQL Retail Data Warehouse."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ── CORS Middleware ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to trusted origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception Handlers ───────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches unhandled errors and returns standardized error response."""
    logger.exception("Global exception handler caught an unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please contact system administrators."}
    )


# ── Route Registrations ──────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(kpis.router)
app.include_router(customers.router)
app.include_router(products.router)
app.include_router(sales.router)
app.include_router(dashboard.router)


@app.get("/")
def read_root() -> dict[str, str]:
    """Exposes basic information about the API service."""
    return {
        "project": "Retail Data Warehouse & Sales Analytics Platform",
        "version": "1.0.0",
        "documentation": "/docs"
    }
