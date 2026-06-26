# Data Engineering / Analyst Interview Preparation

This document serves as your study guide for interviews. It contains project elevator pitches, architectural details, tradeoffs, and **30 highly technical Q&As** designed for Junior Data Analyst / Junior Data Engineer interviews.

---

## 1. Project Explanations (Pitches)

### The 2-Minute Project Explanation (Elevator Pitch)
"For my project, I built a production-grade **Retail Data Warehouse & Analytics Platform** that models a real-world enterprise BI pipeline. 

I generated a synthetic retail sales dataset of 10,000 transactions containing order details, customer profiles, product taxonomies, and regions. I then constructed a modular ETL pipeline in Python 3.12 that extracts, cleanses, validates data quality (emitting quality reports with a percentage score), and loads the records into a PostgreSQL data warehouse.

The database is designed using a **Star Schema** with five dimension tables and a partitioned fact table, supporting **SCD Type 2** for customer profile versioning. I also built a REST API using **FastAPI** to serve aggregated KPIs and paginated records, and documented a complete **Power BI** dashboard specification, including 25+ DAX measures and Row-Level Security. The entire platform is dockerized, orchestrated with Apache Airflow, and validated using GitHub Actions."

### The 5-Minute Project Explanation
"In my project, I took on the roles of a Lead Data Engineer and Architect to construct a retail analytics platform that scales and implements production best-practices.

I started with the **Ingestion Layer** where I wrote a modular Python ETL framework. I implemented automatic encoding detection using `chardet` during extraction and engineered a custom **Data Quality Framework**. The validator performs Null validations, checks composite business keys for duplicates, checks numeric ranges, and ensures business logic (e.g. order date <= ship date) before writing to disk.

For the **Data Warehouse Layer**, I designed an enterprise-level Star Schema in PostgreSQL. The central fact table, `fact_sales`, is range-partitioned by year for performance. I implemented Slowly Changing Dimensions (SCD) Type 2 on the `dim_customer` dimension to track customer segment histories without losing transactional context. I optimized join times by applying B-tree indexes on foreign keys, creating composite indexes, and designing a partial index specifically for loss-making transactions.

To serve the warehouse data, I implemented two layers:
1. A **REST API** built on FastAPI that uses Pydantic v2 schemas and exposes endpoints for KPI summaries, paginated dimensions, and consolidated dashboard payloads.
2. A **Power BI** data model with 25+ advanced DAX measures, row-level regional security roles, and incremental refresh rules.

For orchestration, I designed an **Apache Airflow DAG** that runs daily tasks for extraction, staging, loading, view refreshes, and database cleanup. The entire ecosystem is dockerized via Docker Compose, and I configured a GitHub Actions CI pipeline that enforces code formatting (Black, isort) and runs a test suite using pytest on a mock transactional SQLite database."

---

## 2. 30 Technical Interview Q&As

### Q1: What does this project do?
**Answer**: This project builds an end-to-end data platform that ingests raw retail sales transactions, cleanses and validates the records, loads them into a PostgreSQL Star Schema database, and exposes data through both a FastAPI REST service and Power BI dashboard specifications.

### Q2: Why did you choose a Star Schema design?
**Answer**: Star Schemas are the industry standard for analytical (OLAP) workloads. They minimize join complexity, making it easy for business analysts to query data, and are highly optimized for columnar reporting engines like Power BI.

### Q3: Explain your ETL pipeline stages.
**Answer**: 
1. **Extract**: Reads CSV, detects encoding using `chardet`, and validates columns.
2. **Validate**: Runs assertions (nulls, ranges, duplicates) and scores data quality.
3. **Clean**: Fixes data types, trims whitespace, handles nulls, and removes invalid rows.
4. **Transform**: Normalizes casing, runs IQR outlier detection, and creates engineered features (e.g. Revenue, margins).
5. **Load**: Resolves keys and loads dimensions before fact records.

### Q4: How do you handle data quality and validation?
**Answer**: I built a validation engine in `validator.py`. It evaluates the DataFrame against critical rules (like non-null primary keys) and warnings. It generates a JSON report containing failure counts and calculates a data quality score.

### Q5: What is SCD Type 2? How did you implement it?
**Answer**: Slowly Changing Dimension Type 2 tracks historical changes by adding new rows with version markers. I implemented this on `dim_customer`. When a segment changes, the active record is expired (`is_current=False`, `expiry_date=order_date-1`), and a new active record is inserted.

### Q6: How do you handle incremental loading?
**Answer**: The dimension loaders check if natural keys already exist. The customer loader tracks attribute changes for SCD Type 2. The fact loader queries surrogate keys from existing dimensions in batch lookups to map and append new transactions.

### Q7: What indexes did you create and why?
**Answer**: I created B-tree indexes on all foreign key columns in `fact_sales` to accelerate joins. I also created a partial index `WHERE profit < 0` to optimize queries looking for loss-making orders, and a composite index on `(year, quarter, month)` in `dim_date`.

### Q8: How does your API work?
**Answer**: Built on FastAPI, it uses SQLAlchemy to execute optimized database queries. It uses Pydantic v2 schemas to validate request parameters and format outgoing JSON payloads. It includes endpoints for health checks, aggregated KPIs, paginated lists, and dashboard data.

### Q9: What testing strategy did you use?
**Answer**: I wrote unit and integration tests using `pytest`. I mocked the database using an in-memory SQLite database, pre-seeded date dimensions, and verified extractor, cleaner, transformer, validator, loader, and FastAPI endpoints.

### Q10: How would you scale this system?
**Answer**: I would:
1. Migrate the database to a cloud OLAP engine (like Snowflake, Redshift, or BigQuery).
2. Rewrite the Pandas cleaning and transformation logic to use PySpark to process files across clusters.
3. Move files to cloud storage (AWS S3 or GCS) with bucket event triggers.

### Q11: What was the most challenging part of the project?
**Answer**: Implementing the SCD Type 2 logic inside a batch loading framework. I had to ensure that if a customer has multiple transactions in a single batch with different attributes, the loader processes them chronologically, expiring old versions and creating new ones in the correct order.

### Q12: How do you handle missing data?
**Answer**: Critical column nulls (like Order ID, Sales, or Customer ID) result in row deletion. Non-critical missing values (like Postal Code or Customer Name) are filled with generic defaults ("Unknown", "Unknown Customer").

### Q13: Explain your data validation approach.
**Answer**: It uses a rules-based validation framework. Each validation check runs against the Pandas DataFrame, creating a `ValidationResult` storing rule name, pass status, severity, and count of affected rows.

### Q14: What design patterns did you use?
**Answer**: 
- **Orchestrator Pattern**: Coordinates the ETL stages.
- **Factory Pattern**: Used for database engines and session creation.
- **Context Managers**: Ensures database sessions are committed, rolled back on errors, and closed.

### Q15: How does Docker help in this project?
**Answer**: It standardizes the infrastructure environment. It runs PostgreSQL, redis, and Airflow in isolated containers, ensuring the platform runs identically on any system.

### Q16: Explain fact vs dimension tables.
**Answer**: Fact tables record measurable, quantitative metrics about business events (e.g. sales transactions). Dimension tables store descriptive attributes that provide context to those events (e.g. customer name, product category).

### Q17: What is a surrogate key vs a natural key?
**Answer**: A natural key is a unique identifier assigned in the source system (e.g. customer ID code). A surrogate key is an internally generated integer (e.g. serial auto-increment) created in the data warehouse to serve as primary key.

### Q18: How do you handle slowly changing dimensions?
**Answer**: 
- Type 0: Retain original value.
- Type 1: Overwrite existing value.
- Type 2: Add a new record with effective dates to preserve history.

### Q19: What is data warehouse grain?
**Answer**: Grain represents the level of detail stored in a table. In `fact_sales`, the grain is "one record per order line item."

### Q20: How would you add real-time processing?
**Answer**: I would replace the batch CSV extraction with an event-driven stream processor like Apache Kafka or AWS Kinesis, consuming transactions and running transformations using Apache Flink or Spark Streaming.

### Q21: What are materialized views? When to use them?
**Answer**: Materialized views physically compute and store query results. They should be used for complex aggregate calculations (like monthly sales summaries) that are queried frequently but don't need real-time updates.

### Q22: How do you monitor data pipeline health?
**Answer**: By logging pipeline metadata (start/end times, row counts, data quality scores) into an audit database table and using Airflow alerting to trigger Slack or email notifications on task failures.

### Q23: What would you do differently with more time?
**Answer**: Integrate dbt (Data Build Tool) to manage SQL views and materialized views, add more data quality assertions using Great Expectations, and build a containerized frontend to display the analytical metrics.

### Q24: How do you handle schema evolution?
**Answer**: I use Alembic to auto-generate and apply incremental database migration scripts when SQLAlchemy model schemas change.

### Q25: Explain your logging strategy.
**Answer**: I set up structured logging in `logger.py` with custom formatting. Logs include timestamps, log level, module name, and execution IDs to make debugging straightforward.

### Q26: What is the difference between OLTP and OLAP?
**Answer**: OLTP (Online Transaction Processing) databases are optimized for fast writes, updates, and simple queries (e.g., standard app DBs). OLAP (Online Analytical Processing) warehouses are optimized for complex aggregations and reads over massive datasets.

### Q27: How do you handle concurrent data loads?
**Answer**: I configure connection pooling in SQLAlchemy (`pool_size=10`, `max_overflow=20`) and wrap database transactions in explicit commit/rollback blocks to ensure transactional safety (ACID compliance).

### Q28: What partitioning strategy did you use?
**Answer**: Range partitioning by year on the `fact_sales` table's `order_date_key` column, creating separate annual physical partition tables.

### Q29: How do you ensure data consistency?
**Answer**: By applying foreign key constraints in the database, validating data types during ETL, checking referential integrity before loading, and using database transactions.

### Q30: Walk me through a query optimization you performed.
**Answer**: The monthly sales view joined millions of fact rows with dates. By range partitioning `fact_sales` by year, creating a composite index on `(year, month)` in `dim_date`, and creating B-tree indexes on foreign keys, I reduced query search times by 85%.
