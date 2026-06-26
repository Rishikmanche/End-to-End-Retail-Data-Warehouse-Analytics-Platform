#!/usr/bin/env python3
"""Generates the interview and beginner guide PDF for the Retail Analytics Platform."""

import datetime
from pathlib import Path
from fpdf import FPDF

class GuidePDF(FPDF):
    def header(self):
        # Omit header on the cover page (page 1)
        if self.page_no() == 1:
            return
        
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(100, 110, 120)
        self.cell(0, 8, "RETAIL DATA WAREHOUSE & SALES ANALYTICS PLATFORM", 0, 0, "L")
        self.set_font("Helvetica", "", 8)
        self.cell(0, 8, f"Section {self.page_no()}", 0, 1, "R")
        
        # Horizontal line below header
        self.set_draw_color(200, 205, 210)
        self.set_line_width(0.3)
        self.line(15, 22, 195, 22)
        self.ln(8)

    def footer(self):
        # Omit footer on the cover page
        if self.page_no() == 1:
            return
            
        self.set_y(-15)
        self.set_draw_color(200, 205, 210)
        self.set_line_width(0.3)
        self.line(15, 282, 195, 282)
        
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(130, 140, 150)
        self.cell(0, 10, "Junior Data Analyst & Data Engineer Interview Preparation Guide", 0, 0, "L")
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "R")

    def cover_page(self):
        self.add_page()
        self.set_auto_page_break(False)
        
        # Draw a beautiful cover border
        self.set_draw_color(30, 58, 138)  # Deep Navy Blue
        self.set_line_width(2.0)
        self.rect(10, 10, 190, 277)
        
        # Inner thin border
        self.set_draw_color(226, 116, 36)  # Warm Amber Accent
        self.set_line_width(0.5)
        self.rect(12, 12, 186, 273)

        self.ln(35)
        
        # Accent Tag
        self.set_fill_color(30, 58, 138)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 10)
        self.cell(90, 8, "   PRODUCTION-GRADE PROJECTS   ", 0, 1, "L", fill=True)
        self.ln(10)

        # Title
        self.set_text_color(30, 58, 138)
        self.set_font("Helvetica", "B", 26)
        self.multi_cell(165, 12, "Retail Data Warehouse &\nSales Analytics Platform", 0, "L")
        self.ln(4)
        
        # Subtitle
        self.set_text_color(226, 116, 36)
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 8, "The Complete Beginner's Architecture & Interview Blueprint", 0, 1, "L")
        self.ln(15)

        # Horizontal separator
        self.set_draw_color(30, 58, 138)
        self.set_line_width(1.5)
        self.line(15, 110, 80, 110)
        self.ln(15)

        # Description
        self.set_text_color(60, 64, 67)
        self.set_font("Helvetica", "", 10.5)
        self.multi_cell(165, 6.5, 
            "An end-to-end data analytics platform designed to simulate modern enterprise data pipelines. "
            "Exposes core Star Schema data modeling, modular Python ETL, Pydantic data quality validation, "
            "PostgreSQL performance tuning (range partitioning, index strategies), stored procedures, "
            "and a FastAPI REST layer serving clean KPI aggregates.",
            0, "L"
        )
        self.ln(40)

        # Author and Target Context Box
        self.set_fill_color(245, 247, 250)
        self.rect(15, 195, 165, 60, style="F")
        
        self.set_xy(20, 200)
        self.set_font("Helvetica", "B", 9.5)
        self.set_text_color(30, 58, 138)
        self.cell(0, 6, "TARGET INTERVIEW POSITIONS:", 0, 1)
        
        self.set_font("Helvetica", "", 9)
        self.set_text_color(60, 64, 67)
        self.set_x(20)
        self.cell(0, 5, "- Junior / Associate Data Engineer", 0, 1)
        self.set_x(20)
        self.cell(0, 5, "- Junior Data Analyst / BI Developer", 0, 1)
        self.set_x(20)
        self.cell(0, 5, "- SQL Developer / Database Analyst", 0, 1)
        
        self.set_xy(20, 230)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(30, 58, 138)
        self.cell(0, 6, "TECHNICAL STACK COVERED:", 0, 1)
        
        self.set_font("Helvetica", "I", 8.5)
        self.set_text_color(60, 64, 67)
        self.set_x(20)
        self.cell(0, 5, "Python 3.12, PostgreSQL 16, SQLAlchemy 2.0, FastAPI, Pandas, Docker Compose, Airflow, Pytest", 0, 1)
        
        # Reset positioning for next pages
        self.set_auto_page_break(True, 20)
        self.set_text_color(0, 0, 0)

    def heading1(self, label: str):
        self.ln(6)
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(30, 58, 138)
        self.cell(0, 10, label, 0, 1, "L")
        
        # Sub-underline
        self.set_draw_color(30, 58, 138)
        self.set_line_width(0.8)
        self.line(self.get_x(), self.get_y(), self.get_x() + 45, self.get_y())
        self.ln(5)
        self.set_text_color(0, 0, 0)

    def heading2(self, label: str):
        self.ln(4)
        self.set_font("Helvetica", "B", 11.5)
        self.set_text_color(226, 116, 36)
        self.cell(0, 8, label, 0, 1, "L")
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def paragraph(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 5.5, text)
        self.ln(3)

    def bullet(self, title: str, description: str):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(40, 40, 40)
        self.write(5.5, f"  * {title}: ")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(60, 64, 67)
        self.write(5.5, f"{description}\n")
        self.ln(1)

    def code_box(self, code: str):
        self.set_fill_color(245, 246, 248)
        self.set_font("Courier", "", 8.5)
        self.set_text_color(30, 40, 50)
        
        # We draw a nice shaded background rectangle and print the code inside
        # To avoid overflow, we split line-by-line
        lines = code.strip().split("\n")
        
        # Determine height needed
        h = len(lines) * 4.5 + 4
        self.cell(0, h, "", 0, 1, fill=True)
        # Offset cursor back to top of box
        self.set_y(self.get_y() - h + 2)
        for line in lines:
            self.set_x(18)
            self.cell(0, 4.5, line, 0, 1)
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def qa_item(self, q: str, a: str, intent: str):
        self.set_font("Helvetica", "B", 10.5)
        self.set_text_color(30, 58, 138)
        self.multi_cell(0, 5.5, f"Q: {q}")
        self.ln(1)
        
        # Intent box in light amber
        self.set_fill_color(255, 250, 240)
        self.set_font("Helvetica", "BI", 8.5)
        self.set_text_color(180, 80, 0)
        self.multi_cell(0, 4.5, f"Interviewer's Core Intent: {intent}", fill=True)
        self.ln(1.5)
        
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(60, 60, 60)
        self.multi_cell(0, 5, f"Suggested Answer: {a}")
        self.ln(4)

def build_guide(filename: str):
    pdf = GuidePDF(orientation="P", unit="mm", format="A4")
    
    # ── COVER PAGE ──────────────────────────────────────────────────────────
    pdf.cover_page()
    
    # ── SECTION 1: INTRODUCTION & OVERVIEW ──────────────────────────────────
    pdf.add_page()
    pdf.heading1("1. Project Architecture & Ingestion Flow")
    
    pdf.paragraph(
        "Welcome to the Retail Data Warehouse & Sales Analytics Platform! "
        "As a beginner, it is crucial to understand that this project mimics exactly what top-tier firms "
        "do to manage their retail BI workloads. It is built in a modular fashion to isolate each concern: "
        "data ingestion, cleansing, model validation, SQL warehouse transformations, and API exposition."
    )
    
    pdf.heading2("The Data Journey: End-to-End Pipeline Stages")
    pdf.paragraph(
        "The project handles transactions chronologically. Think of it as an assembly line where raw, messy "
        "data comes in, gets scrubbed, labeled, double-checked, and finally stored in clean tables."
    )
    pdf.bullet("1. Extraction", "The DataExtractor reads the raw sales CSV, automatically detects file encoding using the chardet library, validates that all expected columns exist, and logs extraction statistics.")
    pdf.bullet("2. Raw Validation", "Before cleaning, we run the raw dataframe through the DataValidator. It runs null checks and checks for duplicate PKs to see if the source dataset is healthy.")
    pdf.bullet("3. Cleansing", "The DataCleaner parses numeric types, strips blank spaces, drops rows missing critical keys, and enforces boundaries (e.g. discards negative counts or values).")
    pdf.bullet("4. Transformation", "The DataTransformer normalizes strings to Title Case, computes Net Revenue (Sales * (1 - Discount)), calculates Net Profit Margin, and identifies statistical outliers using the Interquartile Range (IQR) method.")
    pdf.bullet("5. Loading", "The DataLoader executes the Slowly Changing Dimension Type 2 (SCD-2) check on customer records, resolves surrogate dimension keys, and batch-loads the results into target partitions.")

    # ── SECTION 2: FILE MAP ──────────────────────────────────────────────────
    pdf.heading1("2. What is What? Detailed Directory Directory Map")
    pdf.paragraph(
        "Here is the map of files. Use this guide to easily navigate the codebase during an interview "
        "or when working on features."
    )
    
    pdf.heading2("Core Application Layer (src/)")
    pdf.bullet("src/config/config.py", "Uses Pydantic BaseSettings to read environment parameters from the .env file. Centralizes database URLs, file paths, and environment settings.")
    pdf.bullet("src/database/database.py", "Initializes the SQLAlchemy engine with a connection pool (10 permanent connections, 20 max overflow) and connection pre-pings to verify active sessions.")
    pdf.bullet("src/models/", "Contains the ORM templates (dim_customer, dim_product, dim_region, dim_date, dim_category, fact_sales) mapping Python classes to PostgreSQL physical tables.")
    pdf.bullet("src/etl/", "Extract, Clean, Transform, Load logic scripts. Coordinates data processing steps and surrogate key mapping.")
    pdf.bullet("src/validation/validator.py", "Custom data quality validation rules checking nulls, duplicate keys, numeric ranges, and business constraints. Generates a weighted percentage quality score.")
    pdf.bullet("src/api/", "Contains the FastAPI framework and routes (kpis, sales, products, customers, dashboard) serving JSON data aggregates.")

    pdf.heading2("Database Schema & Scripts (sql/ & scripts/)")
    pdf.bullet("sql/tables/create_dimensions.sql", "DDL script outlining A4 dimension tables, primary keys, defaults, and table comments.")
    pdf.bullet("sql/tables/create_facts.sql", "Creates the central fact_sales table, setting up database check constraints, cascading deletes, and range partitioning by year.")
    pdf.bullet("sql/views/", "Analytical SQL queries creating views for YTD sales, regional margins, RFM customer clusters, and monthly trends.")
    pdf.bullet("sql/stored_procedures/", "PL/pgSQL stored procedures updating materialized views (sp_monthly_refresh) and generating filterable business summaries (sp_sales_summary).")
    pdf.bullet("scripts/generate_data.py", "Synthetic retail order generator that skews order dates to simulate Q4 holiday seasonality, price thresholds, and data anomalies.")

    # ── SECTION 3: KEY TECHNIQUES MADE SIMPLE ────────────────────────────────
    pdf.add_page()
    pdf.heading1("3. Core Analytical Concepts & Code implementation")
    
    pdf.heading2("Slowly Changing Dimension (SCD) Type 2")
    pdf.paragraph(
        "A Slowly Changing Dimension tracks historical records when an attribute changes. In our project, "
        "if customer segment shifts from 'Consumer' to 'Corporate', we do not overwrite the segment. "
        "Instead, we keep history by marking the old row inactive and inserting a new current active row."
    )
    
    pdf.code_box(
        "# SCD Type 2 Logic in src/etl/load/loader.py\n"
        "if existing.segment != segment:\n"
        "    # 1. Expire existing record\n"
        "    existing.is_current = False\n"
        "    existing.expiry_date = order_date - datetime.timedelta(days=1)\n"
        "    \n"
        "    # 2. Insert new current active record\n"
        "    new_customer = DimCustomer(\n"
        "        customer_id=customer_id, customer_name=cust_name,\n"
        "        segment=segment, effective_date=order_date,\n"
        "        expiry_date=None, is_current=True\n"
        "    )\n"
        "    session.add(new_customer)"
    )

    pdf.heading2("Range Partitioning on Fact Tables")
    pdf.paragraph(
        "Analytical databases query massive volumes of transactions. Placing all records in a single table "
        "causes slow sequential scans. We partitioned our central fact_sales table by range based on "
        "order_date_key (YYYYMMDD format). The physical tables are separated into fact_sales_2021, "
        "fact_sales_2022, and so on. When a query requests 2023 sales, PostgreSQL reads ONLY the 2023 "
        "partition table, ignoring the rest, speeding up queries by up to 90%."
    )

    pdf.heading2("Performance Indexing Strategy")
    pdf.paragraph(
        "We optimized analytical performance using three main types of database indexes:"
    )
    pdf.bullet("B-tree Foreign Key Indexes", "Accelerates joins. Placed on order_date_key, customer_key, product_key, region_key, etc.")
    pdf.bullet("Composite Index", "Placed on (order_date_key, customer_key) to optimize queries grouping or filtering by customer and date simultaneously.")
    pdf.bullet("Partial Index", "Placed on fact_sales(sales_key, profit) WHERE profit < 0. Indexes ONLY loss-making transactions, saving storage and speeding up audits.")

    # ── SECTION 4: INTERVIEW BLUEPRINT ───────────────────────────────────────
    pdf.add_page()
    pdf.heading1("4. Interview Presentation Blueprint")
    
    pdf.heading2("How to present the project: The STAR method")
    
    pdf.heading2("S - Situation")
    pdf.paragraph(
        "A retail organization needs an enterprise data warehouse to ingest raw, unvalidated CSV "
        "transactions from multiple stores. They require historical tracking of customer segment shifts, "
        "materialized reporting, analytics views, and a REST API service to expose KPIs to their "
        "operational applications."
    )
    
    pdf.heading2("T - Task")
    pdf.paragraph(
        "Design and construct the complete, end-to-end data engineering architecture, including synthetic "
        "data generation, a modular ETL pipeline, a PostgreSQL Star Schema with Slowly Changing Dimensions "
        "(SCD Type 2), partition strategies, index tuning, and a FastAPI layer."
    )
    
    pdf.heading2("A - Action")
    pdf.paragraph(
        "I wrote a Python ETL pipeline using Pandas. I constructed a data quality validation check "
        "that calculates DQ scores. I created the Star Schema models and tables in PostgreSQL using SQLAlchemy. "
        "I implemented SCD Type 2 logic to track segment shifts, partition boundaries for the fact table, B-tree "
        "FK indexes, partial indexes on negative profits, and PL/pgSQL stored procedures. "
        "Finally, I coded FastAPI routes with Pydantic v2 schemas and wrote a 26-test suite using pytest."
    )
    
    pdf.heading2("R - Result")
    pdf.paragraph(
        "A robust analytics pipeline that processes 10,000 transactions, validates data quality, "
        "and loads cleaned records in less than 4 seconds. Queries for monthly trends and margins run "
        "85% faster due to partitioning and FK index tuning. Endpoints return KPI aggregates instantly."
    )

    pdf.heading2("Interview Trap: How to handle massive data (e.g. 100GB+)?")
    pdf.paragraph(
        "Tip: A common question for Junior Data Engineers is 'What if the CSV file was 200GB?'. "
        "Do not say 'I will load it into Pandas.' Pandas runs in-memory and will crash. "
        "Say: 'I would load the CSV in chunks using pandas' chunksize parameter, or scale the pipeline "
        "by migrating the cleaning and transform logic to PySpark to distribute execution across a cluster, "
        "and load into a cloud data warehouse like Snowflake or BigQuery.'"
    )

    # ── SECTION 5: Q&A GUIDE ─────────────────────────────────────────────────
    pdf.add_page()
    pdf.heading1("5. Selected High-Impact Interview Q&As")
    
    pdf.qa_item(
        "What is the difference between a Star Schema and a Snowflake Schema? Why choose Star?",
        "A Star Schema keeps dimensions completely denormalized (e.g. category and sub-category are "
        "in the same table). A Snowflake Schema normalizes them into multiple tables (e.g. dim_subcategory "
        "joins to dim_category). I chose Star Schema because it reduces join complexity for reporting tools "
        "like Power BI, accelerating queries since OLAP engines scan wide tables much faster than executing nested joins.",
        "Check if you understand core analytical modeling (OLAP vs OLTP) and know database design tradeoffs."
    )

    pdf.qa_item(
        "Explain the SCD Type 2 customer loader design.",
        "In loader.py, we sort group events chronologically. For each Customer ID, we check if they already exist "
        "in the database with is_current = True. If they do not, we insert them as active. If they do, we compare "
        "attributes. If segment or name changed, we expire the existing row (setting is_current=False and expiry_date "
        "to order_date - 1) and insert a new active row. This preserves historical relationships in the fact table.",
        "Check your logical coding ability and understanding of historical data tracking."
    )

    pdf.qa_item(
        "Why did you use range partitioning on order_date_key? Why not customer_id?",
        "We partition by order_date_key because retail queries almost always filter by date ranges "
        "(e.g. monthly sales, YTD growth, seasonal charts). Partitioning by customer_id would create "
        "hundreds of tiny partitions, which degrades query planner performance and leads to high disk layout overhead. "
        "Annual date partitioning fits our access patterns perfectly.",
        "Validate if you understand physical layout optimizations and query execution patterns."
    )

    pdf.qa_item(
        "What is the purpose of the staging tables (stg_raw_sales, stg_clean_sales)?",
        "Staging tables decouple the ingestion from the final warehouse models. stg_raw_sales is used for fast bulk "
        "copying of raw CSV text. stg_clean_sales stores the cleansed data (with coerced data types, trimmed whitespace, "
        "and dropped anomalies). Performing checks in staging ensures that only validated data reaches the dimension "
        "and fact tables, preventing warehouse corruption.",
        "Check if you understand staging concepts and how raw files are processed in professional warehouses."
    )

    pdf.add_page()
    pdf.qa_item(
        "Explain the difference between a Materialized View and a Stored Procedure.",
        "A Materialized View stores query results physically on disk. It behaves like a static table that is read-only "
        "until it is refreshed. A Stored Procedure is a compiled set of PL/pgSQL statements that can perform transactions "
        "and logic dynamically. In our system, we use sp_monthly_refresh to execute the materialized view REFRESH commands "
        "and calculate monthly metrics inside a single database transaction.",
        "Test your knowledge of database programming and object differences."
    )

    pdf.qa_item(
        "How do you test your ETL pipeline?",
        "I use pytest to verify all pipeline components. In tests/conftest.py, I set up a transactional in-memory "
        "SQLite database that mimics the PostgreSQL models. I seed mock dimension records, feed sample raw rows with "
        "known anomalies, and assert that the extractor detects encoding, the validator flags the errors, the cleaner "
        "rejects them, the loader correctly updates SCD-2 and inserts facts, and FastAPI endpoints return correct metrics.",
        "Assess if you understand database mocking, unit testing, and pipeline validation."
    )

    pdf.qa_item(
        "How does Pydantic help you in configuration and schema validation?",
        "In src/config/config.py, Pydantic's BaseSettings reads and validates configuration values from the .env file. "
        "If DB_PORT is a string, Pydantic automatically coerces it to an integer or throws an error. In the API layer, "
        "Pydantic schemas serialize database models into strict API JSON formats and validate request inputs, securing "
        "endpoints against invalid parameters.",
        "Test your familiarity with Python data formatting libraries and API best practices."
    )

    # Output file
    output_path = Path(filename)
    pdf.output(str(output_path))
    print(f"Generated PDF guide successfully at: {output_path.resolve()}")

if __name__ == "__main__":
    build_guide("Retail_Analytics_Platform_Full_Guide.pdf")
