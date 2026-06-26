"""Data loader module for the ETL pipeline.

Handles loading cleansed and transformed pandas DataFrames into PostgreSQL
dimension and fact tables. Implements Slowly Changing Dimension Type 2 (SCD-2)
for dim_customer, handles surrogate key resolution, and performs batch loading.
"""

from __future__ import annotations

import datetime
from typing import Any
import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.models.dim_category import DimCategory
from src.models.dim_customer import DimCustomer
from src.models.dim_date import DimDate
from src.models.dim_product import DimProduct
from src.models.dim_region import DimRegion
from src.models.fact_sales import FactSales
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataLoader:
    """Loads transformed retail sales data into PostgreSQL Star Schema."""

    def __init__(self, engine: Engine, batch_size: int = 1000) -> None:
        self.engine = engine
        self.batch_size = batch_size
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.logger = logger

    def load_all(self, df: pd.DataFrame) -> dict[str, int]:
        """Loads all dimensions and facts from the DataFrame.

        Args:
            df: Transformed input DataFrame.

        Returns:
            A dictionary containing loaded row counts per table.
        """
        self.logger.info("Starting warehouse data loading...")
        metrics = {}

        # 1. Load date dimension
        metrics["dim_date"] = self.load_date_dimension(df)

        # 2. Load category dimension
        metrics["dim_category"] = self.load_category_dimension(df)

        # 3. Load region dimension
        metrics["dim_region"] = self.load_region_dimension(df)

        # 4. Load customer dimension (SCD Type 2)
        metrics["dim_customer"] = self.load_customer_dimension(df)

        # 5. Load product dimension
        metrics["dim_product"] = self.load_product_dimension(df)

        # 6. Load fact sales table
        metrics["fact_sales"] = self.load_fact_sales(df)

        self.logger.info("Finished warehouse data loading. Metrics: %s", metrics)
        return metrics

    def load_date_dimension(self, df: pd.DataFrame) -> int:
        """Generates and loads date dimension from minimum to maximum dates in the DataFrame."""
        self.logger.info("Loading Date dimension...")
        
        # Determine date range
        order_dates = df["Order Date"].dropna()
        ship_dates = df["Ship Date"].dropna()
        
        if order_dates.empty or ship_dates.empty:
            self.logger.warning("Empty date columns. Skipping date dimension loading.")
            return 0
            
        order_dates_dt = pd.to_datetime(order_dates)
        ship_dates_dt = pd.to_datetime(ship_dates)
            
        min_date = min(order_dates_dt.min(), ship_dates_dt.min()).date()
        max_date = max(order_dates_dt.max(), ship_dates_dt.max()).date()
        
        # Add buffer (e.g., start of year to end of year)
        start_date = datetime.date(min_date.year, 1, 1)
        end_date = datetime.date(max_date.year, 12, 31)
        
        self.logger.info("Generating date range from %s to %s", start_date, end_date)
        
        dates_to_insert = []
        current_date = start_date
        
        # Build date items
        while current_date <= end_date:
            date_key = int(current_date.strftime("%Y%m%d"))
            
            # Fiscal calculations (assumes fiscal year starts in April)
            # April is Month 4, so Month 4 is fiscal month 1
            fiscal_month = (current_date.month - 4) % 12 + 1
            fiscal_quarter = (fiscal_month - 1) // 3 + 1
            # If month is Jan, Feb, Mar, fiscal year is current year - 1
            fiscal_year = current_date.year if current_date.month >= 4 else current_date.year - 1
            
            dates_to_insert.append({
                "date_key": date_key,
                "full_date": current_date,
                "day_of_week": current_date.weekday() + 1,  # 1-7
                "day_name": current_date.strftime("%A"),
                "day_of_month": current_date.day,
                "day_of_year": current_date.timetuple().tm_yday,
                "week_of_year": current_date.isocalendar()[1],
                "month": current_date.month,
                "month_name": current_date.strftime("%B"),
                "quarter": (current_date.month - 1) // 3 + 1,
                "year": current_date.year,
                "is_weekend": current_date.weekday() in (5, 6),
                "is_holiday": False,  # Placeholder for federal holidays
                "fiscal_quarter": fiscal_quarter,
                "fiscal_year": fiscal_year,
            })
            current_date += datetime.timedelta(days=1)

        # Bulk upsert logic using SQLAlchemy
        count = 0
        with self.SessionLocal() as session:
            # Query existing date keys to avoid duplicate attempts
            existing_keys = set(r[0] for r in session.execute(select(DimDate.date_key)).fetchall())
            new_dates = [d for d in dates_to_insert if d["date_key"] not in existing_keys]
            
            if new_dates:
                # Perform bulk inserts in chunks
                for i in range(0, len(new_dates), self.batch_size):
                    chunk = new_dates[i:i + self.batch_size]
                    session.execute(
                        DimDate.__table__.insert(),
                        chunk
                    )
                    count += len(chunk)
                session.commit()
                self.logger.info("Inserted %d new date records.", count)
            else:
                self.logger.info("All dates already exist in warehouse.")
        return count

    def load_category_dimension(self, df: pd.DataFrame) -> int:
        """Loads unique categories and sub-categories."""
        self.logger.info("Loading Category dimension...")
        
        # Group by Category/Sub-Category to get unique entries
        cat_df = df[["Category", "Sub-Category"]].dropna().drop_duplicates()
        
        count = 0
        with self.SessionLocal() as session:
            # Get existing categories
            existing = session.execute(select(DimCategory.category_name, DimCategory.sub_category)).fetchall()
            existing_set = {(r[0], r[1]) for r in existing}

            new_cats = []
            for _, row in cat_df.iterrows():
                cat_name = row["Category"]
                sub_cat = row["Sub-Category"]
                if (cat_name, sub_cat) not in existing_set:
                    # Generate category_id, e.g. FURN-BOOKCASES
                    cat_id = f"{cat_name[:4].upper()}-{sub_cat.replace(' ', '').upper()}"
                    new_cats.append({
                        "category_id": cat_id,
                        "category_name": cat_name,
                        "sub_category": sub_cat,
                        "description": f"Product Category: {cat_name}, Sub-Category: {sub_cat}",
                        "created_at": datetime.datetime.utcnow(),
                        "updated_at": datetime.datetime.utcnow(),
                    })
            
            if new_cats:
                session.execute(DimCategory.__table__.insert(), new_cats)
                session.commit()
                count = len(new_cats)
                self.logger.info("Inserted %d new category records.", count)
            else:
                self.logger.info("All category records already exist.")
        return count

    def load_region_dimension(self, df: pd.DataFrame) -> int:
        """Loads unique geography/region combinations."""
        self.logger.info("Loading Region dimension...")
        
        geo_cols = ["Country", "Region", "State", "City", "Postal Code"]
        region_df = df[geo_cols].dropna(subset=["Country", "State", "City"]).drop_duplicates()
        
        count = 0
        with self.SessionLocal() as session:
            # Look up existing regions
            existing = session.execute(
                select(DimRegion.country, DimRegion.state, DimRegion.city, DimRegion.postal_code)
            ).fetchall()
            existing_set = {(r[0], r[1], r[2], str(r[3]) if r[3] is not None else "Unknown") for r in existing}

            new_regions = []
            for _, row in region_df.iterrows():
                country = row["Country"]
                region = row["Region"]
                state = row["State"]
                city = row["City"]
                
                raw_post = row["Postal Code"]
                if pd.isna(raw_post):
                    postal_code = "Unknown"
                elif isinstance(raw_post, (int, float)):
                    postal_code = str(int(raw_post))
                else:
                    postal_code = str(raw_post).split(".")[0] if "." in str(raw_post) else str(raw_post)
                
                if (country, state, city, postal_code) not in existing_set:
                    new_regions.append({
                        "country": country,
                        "region": region,
                        "state": state,
                        "city": city,
                        "postal_code": postal_code,
                        "created_at": datetime.datetime.utcnow(),
                        "updated_at": datetime.datetime.utcnow(),
                    })
                    # Add to existing_set so we don't insert duplicates within the same batch
                    existing_set.add((country, state, city, postal_code))

            if new_regions:
                session.execute(DimRegion.__table__.insert(), new_regions)
                session.commit()
                count = len(new_regions)
                self.logger.info("Inserted %d new region records.", count)
            else:
                self.logger.info("All region records already exist.")
        return count

    def load_customer_dimension(self, df: pd.DataFrame) -> int:
        """Loads customers implementing Slowly Changing Dimension Type 2 (SCD-2)."""
        self.logger.info("Loading Customer dimension (SCD-2)...")
        
        cust_df = df[["Customer ID", "Customer Name", "Segment", "Order Date"]].dropna(subset=["Customer ID", "Customer Name"])
        # Group by Customer ID and pick the latest record per customer (or chronological order)
        cust_df = cust_df.sort_values("Order Date")
        
        count = 0
        today = datetime.date.today()
        
        with self.SessionLocal() as session:
            for customer_id, group in cust_df.groupby("Customer ID"):
                # Get the latest details from the files
                latest_row = group.iloc[-1]
                cust_name = latest_row["Customer Name"]
                segment = latest_row["Segment"]
                raw_date = latest_row["Order Date"]
                order_date = pd.to_datetime(raw_date).date() if isinstance(raw_date, str) else raw_date.date()

                # Check if customer exists in the warehouse
                stmt = select(DimCustomer).where(
                    DimCustomer.customer_id == customer_id,
                    DimCustomer.is_current == True
                )
                existing = session.execute(stmt).scalar_one_or_none()

                if existing is None:
                    # New customer: insert new active record
                    new_customer = DimCustomer(
                        customer_id=customer_id,
                        customer_name=cust_name,
                        segment=segment,
                        effective_date=order_date,
                        expiry_date=None,
                        is_current=True,
                        created_at=datetime.datetime.utcnow(),
                        updated_at=datetime.datetime.utcnow()
                    )
                    session.add(new_customer)
                    count += 1
                else:
                    # Existing active customer: check for changes
                    if existing.customer_name != cust_name or existing.segment != segment:
                        # Value has changed! SCD Type 2 logic:
                        # 1. Expire existing record
                        existing.is_current = False
                        existing.expiry_date = order_date - datetime.timedelta(days=1)
                        existing.updated_at = datetime.datetime.utcnow()
                        session.add(existing)
                        
                        # 2. Insert new current record
                        new_customer = DimCustomer(
                            customer_id=customer_id,
                            customer_name=cust_name,
                            segment=segment,
                            effective_date=order_date,
                            expiry_date=None,
                            is_current=True,
                            created_at=datetime.datetime.utcnow(),
                            updated_at=datetime.datetime.utcnow()
                        )
                        session.add(new_customer)
                        count += 1
            
            session.commit()
            self.logger.info("Completed SCD Type 2 customer updates. %d new/updated customer records created.", count)
        return count

    def load_product_dimension(self, df: pd.DataFrame) -> int:
        """Loads unique products, resolving category foreign keys."""
        self.logger.info("Loading Product dimension...")
        
        prod_df = df[["Product ID", "Product Name", "Category", "Sub-Category"]].dropna(subset=["Product ID", "Product Name"]).drop_duplicates(subset=["Product ID"])

        count = 0
        with self.SessionLocal() as session:
            # Cache category lookups (Category + Sub-Category -> Category Key)
            cats = session.execute(select(DimCategory.category_key, DimCategory.category_name, DimCategory.sub_category)).fetchall()
            cat_cache = {(r[1], r[2]): r[0] for r in cats}

            # Cache existing products
            existing = session.execute(select(DimProduct.product_id)).fetchall()
            existing_set = {r[0] for r in existing}

            new_prods = []
            for _, row in prod_df.iterrows():
                prod_id = row["Product ID"]
                prod_name = row["Product Name"]
                cat_name = row["Category"]
                sub_cat = row["Sub-Category"]
                
                if prod_id not in existing_set:
                    cat_key = cat_cache.get((cat_name, sub_cat))
                    if cat_key is None:
                        # Fallback: create category dynamically if cached lookup fails
                        self.logger.warning("Category cache miss for Category: %s, Sub-Category: %s. Loading product %s with null category_key.", cat_name, sub_cat, prod_id)
                    
                    new_prods.append({
                        "product_id": prod_id,
                        "product_name": prod_name[:500],  # Truncate if too long
                        "category_key": cat_key,
                        "sub_category": sub_cat,
                        "created_at": datetime.datetime.utcnow(),
                        "updated_at": datetime.datetime.utcnow(),
                    })

            if new_prods:
                # Batch inserts
                for i in range(0, len(new_prods), self.batch_size):
                    chunk = new_prods[i:i + self.batch_size]
                    session.execute(DimProduct.__table__.insert(), chunk)
                    count += len(chunk)
                session.commit()
                self.logger.info("Inserted %d new product records.", count)
            else:
                self.logger.info("All product records already exist.")
        return count

    def load_fact_sales(self, df: pd.DataFrame) -> int:
        """Loads fact sales records by resolving surrogate keys for each transaction."""
        self.logger.info("Loading Sales facts...")

        count = 0
        with self.SessionLocal() as session:
            # 1. Fetch lookup caches from DB to avoid N+1 queries during loading
            customers = session.execute(select(DimCustomer.customer_key, DimCustomer.customer_id).where(DimCustomer.is_current == True)).fetchall()
            cust_cache = {r[1]: r[0] for r in customers}

            products = session.execute(select(DimProduct.product_key, DimProduct.product_id)).fetchall()
            prod_cache = {r[1]: r[0] for r in products}

            regions = session.execute(select(DimRegion.region_key, DimRegion.country, DimRegion.state, DimRegion.city, DimRegion.postal_code)).fetchall()
            # Compound key lookup: (Country, State, City, Postal Code) -> Region Key
            region_cache = {(r[1], r[2], r[3], r[4]): r[0] for r in regions}

            categories = session.execute(select(DimCategory.category_key, DimCategory.category_name, DimCategory.sub_category)).fetchall()
            cat_cache = {(r[1], r[2]): r[0] for r in categories}

            # Cache dates as set of existing keys
            dates = session.execute(select(DimDate.date_key)).fetchall()
            date_cache = {r[0] for r in dates}

            new_facts = []
            skipped_rows = 0

            # Iterate over the source dataframe
            for idx, row in df.iterrows():
                order_id = row["Order ID"]
                cust_id = row["Customer ID"]
                prod_id = row["Product ID"]
                country = row["Country"]
                state = row["State"]
                city = row["City"]
                postal_code = row["Postal Code"]
                cat_name = row["Category"]
                sub_cat = row["Sub-Category"]

                order_date = row["Order Date"]
                ship_date = row["Ship Date"]

                # Generate date keys (YYYYMMDD integer)
                order_dt = pd.to_datetime(order_date)
                ship_dt = pd.to_datetime(ship_date)
                order_date_key = int(order_dt.strftime("%Y%m%d"))
                ship_date_key = int(ship_dt.strftime("%Y%m%d"))

                # Validate dates exist in dim_date, if not fallback to generic/default keys
                if order_date_key not in date_cache:
                    self.logger.warning("Order Date Key %d not found in Date Dimension. Skipping row.", order_date_key)
                    skipped_rows += 1
                    continue
                if ship_date_key not in date_cache:
                    self.logger.warning("Ship Date Key %d not found in Date Dimension. Skipping row.", ship_date_key)
                    skipped_rows += 1
                    continue

                # Resolve surrogate keys
                cust_key = cust_cache.get(cust_id)
                prod_key = prod_cache.get(prod_id)
                region_key = region_cache.get((country, state, city, postal_code))
                cat_key = cat_cache.get((cat_name, sub_cat))

                if not cust_key:
                    self.logger.warning("Missing Customer Key for ID: %s. Skipping transaction.", cust_id)
                    skipped_rows += 1
                    continue
                if not prod_key:
                    self.logger.warning("Missing Product Key for ID: %s. Skipping transaction.", prod_id)
                    skipped_rows += 1
                    continue
                if not region_key:
                    # Fallback lookup without postal code if not matching exactly
                    fallback_regions = [k for k in region_cache.keys() if k[0] == country and k[1] == state and k[2] == city]
                    if fallback_regions:
                        region_key = region_cache[fallback_regions[0]]
                    else:
                        self.logger.warning("Missing Region Key for: %s, %s, %s. Skipping transaction.", country, state, city)
                        skipped_rows += 1
                        continue
                if not cat_key:
                    self.logger.warning("Missing Category Key for Category: %s, Sub-Category: %s. Skipping transaction.", cat_name, sub_cat)
                    skipped_rows += 1
                    continue

                # Quantities/measures
                sales = float(row["Sales"])
                quantity = int(row["Quantity"])
                discount = float(row["Discount"])
                profit = float(row["Profit"])
                revenue = float(row["Revenue"])
                profit_margin = float(row["Profit_Margin"])
                ship_mode = row["Ship Mode"]

                new_facts.append({
                    "order_id": order_id,
                    "order_date_key": order_date_key,
                    "ship_date_key": ship_date_key,
                    "customer_key": cust_key,
                    "product_key": prod_key,
                    "region_key": region_key,
                    "category_key": cat_key,
                    "ship_mode": ship_mode,
                    "sales": sales,
                    "quantity": quantity,
                    "discount": discount,
                    "profit": profit,
                    "revenue": revenue,
                    "profit_margin": profit_margin,
                    "created_at": datetime.datetime.utcnow(),
                    "updated_at": datetime.datetime.utcnow(),
                })

            if skipped_rows > 0:
                self.logger.warning("Skipped %d rows during fact loading due to key resolution failures.", skipped_rows)

            # Insert fact sales in chunks
            if new_facts:
                for i in range(0, len(new_facts), self.batch_size):
                    chunk = new_facts[i:i + self.batch_size]
                    session.execute(FactSales.__table__.insert(), chunk)
                    count += len(chunk)
                session.commit()
                self.logger.info("Inserted %d fact sales records.", count)
            else:
                self.logger.info("No new fact sales records to insert.")

        return count
