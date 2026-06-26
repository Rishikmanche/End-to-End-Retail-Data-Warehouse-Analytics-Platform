"""Apache Airflow DAG for Retail Analytics Platform ETL workflow.

Orchestrates daily data ingestion, validations, and loading operations.
Defines retry logic, logging metrics, and error alerting mechanisms.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# Default arguments for tasks
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": datetime.timedelta(minutes=5),
}


def run_etl_pipeline() -> str:
    """Invokes the ETLPipeline orchestrator inside the Airflow worker context."""
    from src.config.config import get_settings
    from src.etl.pipeline import ETLPipeline
    
    settings = get_settings()
    pipeline = ETLPipeline(settings)
    
    # Run pipeline on default raw CSV file
    result = pipeline.run("superstore_sales.csv")
    
    if result.status == "FAILED":
        raise RuntimeError(f"ETL pipeline run failed. Errors: {result.errors}")
    elif result.status == "QUALITY_FAILURE":
        raise ValueError(f"ETL pipeline completed with critical quality failures. Errors: {result.errors}")
        
    return f"Pipeline completed successfully. Loaded {result.rows_loaded} sales facts."


def refresh_materialized_views() -> str:
    """Refreshes reporting materialized views in the warehouse."""
    from src.database.database import engine
    from src.warehouse.manager import WarehouseManager
    
    manager = WarehouseManager(engine)
    manager.refresh_materialized_views(concurrently=False)
    return "Materialized views refreshed."


def run_vacuum_analyze() -> str:
    """Optimizes database indexing and query planner stats."""
    from src.database.database import engine
    from src.warehouse.manager import WarehouseManager
    
    manager = WarehouseManager(engine)
    manager.vacuum_analyze()
    return "Vacuum Analyze complete."


# Define DAG
with DAG(
    dag_id="retail_warehouse_etl",
    default_args=default_args,
    description="Daily ETL pipeline to ingest and load retail sales transactions",
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
    tags=["retail", "data-warehouse", "etl"],
) as dag:

    # 1. Task to run full modular ETL pipeline
    task_run_etl = PythonOperator(
        task_id="run_etl_pipeline",
        python_callable=run_etl_pipeline,
    )

    # 2. Task to refresh materialized views
    task_refresh_views = PythonOperator(
        task_id="refresh_materialized_views",
        python_callable=refresh_materialized_views,
    )

    # 3. Task to perform vacuum analyze on tables
    task_vacuum_db = PythonOperator(
        task_id="run_vacuum_analyze",
        python_callable=run_vacuum_analyze,
    )

    # Task Dependencies
    task_run_etl >> task_refresh_views >> task_vacuum_db
