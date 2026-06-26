"""Synthetic retail sales data generator.

Generates a realistic Superstore-style dataset containing ~10,000 transactions
spanning 2021-01-01 to 2024-12-31, featuring seasonal trends, customer segments,
hierarchical categories, geographic distribution, and financial calculations.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import os
import random
from pathlib import Path

# Seed for reproducibility
random.seed(42)

# --- Catalogs ---

SEGMENTS = ["Consumer", "Corporate", "Home Office"]
SEGMENT_WEIGHTS = [0.52, 0.30, 0.18]

SHIP_MODES = ["Standard Class", "Second Class", "First Class", "Same Day"]
SHIP_MODE_WEIGHTS = [0.60, 0.20, 0.15, 0.05]

GEOGRAPHIES = [
    # Region, Country, State, City, Postal Code range
    ("East", "United States", "New York", "New York City", "10001"),
    ("East", "United States", "New York", "Albany", "12201"),
    ("East", "United States", "Pennsylvania", "Philadelphia", "19104"),
    ("East", "United States", "Massachusetts", "Boston", "02108"),
    ("West", "United States", "California", "Los Angeles", "90012"),
    ("West", "United States", "California", "San Francisco", "94102"),
    ("West", "United States", "California", "San Diego", "92101"),
    ("West", "United States", "Washington", "Seattle", "98101"),
    ("Central", "United States", "Texas", "Houston", "77002"),
    ("Central", "United States", "Texas", "Dallas", "75201"),
    ("Central", "United States", "Illinois", "Chicago", "60601"),
    ("Central", "United States", "Michigan", "Detroit", "48201"),
    ("South", "United States", "Florida", "Miami", "33101"),
    ("South", "United States", "Georgia", "Atlanta", "30303"),
    ("South", "United States", "North Carolina", "Charlotte", "28202"),
    ("South", "United States", "Tennessee", "Nashville", "37201"),
]

PRODUCT_HIERARCHY = {
    "Furniture": {
        "Bookcases": ["Global Library Bookcase", "Atlantic Metal Bookcase", "Sauder Heritage Bookcase"],
        "Chairs": ["Office Star Executive Chair", "HON Comfort Task Chair", "Harbour Mesh Task Chair"],
        "Furnishings": ["Eldon Desk Accessory", "3M Anti-Glare Screen Filter", "Executive Desk Pad"],
        "Tables": ["Bush Somerset Desk", "Baster Conference Table", "Cherry wood Dining Table"],
    },
    "Office Supplies": {
        "Appliances": ["Krups Coffee Maker", "Hamilton Beach Microwave", "Hoover Power Sweep Vacuum"],
        "Art": ["Crayola Colored Pencils", "Prismacolor Art Markers", "Dixon Ticonderoga Pencils"],
        "Binders": ["Wilson Jones 3-Ring Binder", "GBC Ring Binder", "Acco Pressboard Binder"],
        "Envelopes": ["Mead Kraft Envelopes", "Tyvek Mailing Envelopes", "Self-Seal Window Envelopes"],
        "Fasteners": ["Ideal Paper Clips", "Acco Binder Clips", "Rubber Bands Size 33"],
        "Labels": ["Avery Mailing Labels", "Zebra Thermal Labels", "Dymo Labeling Tape"],
        "Paper": ["Hammermill Copy Paper", "Xerox Multipurpose Paper", "Green Forest Recycled Paper"],
        "Storage": ["Tenex File Pocket", "Fellowes Banker Box", "Stackable Storage Drawers"],
        "Supplies": ["Fiskars Scissors", "Acme Stapler", "Guillotine Paper Trimmer"],
    },
    "Technology": {
        "Accessories": ["Logitech Wireless Mouse", "SanDisk 64GB USB Flash Drive", "Anker PowerPort Charger"],
        "Copiers": ["Canon ImageCLASS Copier", "Brother Monochrome Copier", "Hewlett Packard Laser Copier"],
        "Machines": ["Star Micronics Receipt Printer", "Epson Label Printer", "Lexmark Fax Machine"],
        "Phones": ["Apple iPhone 13", "Samsung Galaxy S22", "Polycom VoIP Desk Phone"],
    }
}

FIRST_NAMES = [
    "John", "Jane", "Robert", "Mary", "James", "Patricia", "Michael", "Jennifer", 
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley"
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Garcia", 
    "Rodriguez", "Wilson", "Martinez", "Anderson", "Taylor", "Thomas", "Hernandez", "Moore",
    "Martin", "Jackson", "Thompson", "White", "Lopez", "Lee", "Gonzalez", "Harris",
    "Clark", "Lewis", "Robinson", "Walker", "Perez", "Hall", "Young", "Allen"
]


def generate_customers(count: int = 800) -> list[dict]:
    """Generates customer master records."""
    customers = []
    for i in range(count):
        cust_id = f"{random.choice(['CG', 'CS', 'HO'])}-{10000 + i}"
        cust_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        segment = random.choices(SEGMENTS, weights=SEGMENT_WEIGHTS)[0]
        customers.append({
            "customer_id": cust_id,
            "customer_name": cust_name,
            "segment": segment
        })
    return customers


def generate_products(count: int = 1000) -> list[dict]:
    """Generates product master records from taxonomy."""
    products = []
    for i in range(count):
        category = random.choice(list(PRODUCT_HIERARCHY.keys()))
        sub_category = random.choice(list(PRODUCT_HIERARCHY[category].keys()))
        name_template = random.choice(PRODUCT_HIERARCHY[category][sub_category])
        
        prod_id = f"{category[:3].upper()}-{sub_category[:4].upper()}-{10000000 + i}"
        prod_name = f"{name_template} Model {random.randint(100, 999)}"
        
        products.append({
            "product_id": prod_id,
            "category": category,
            "sub_category": sub_category,
            "product_name": prod_name
        })
    return products


def generate_transactions(
    target_count: int,
    customers: list[dict],
    products: list[dict]
) -> list[dict]:
    """Generates transactional records."""
    transactions = []
    
    start_date = datetime.date(2021, 1, 1)
    end_date = datetime.date(2024, 12, 31)
    total_days = (end_date - start_date).days

    order_counter = 100000

    # Pricing base rules per Category
    category_prices = {
        "Furniture": (50.0, 1500.0, 0.15),      # min, max, cost_ratio
        "Office Supplies": (2.0, 200.0, 0.40),
        "Technology": (100.0, 3000.0, 0.20)
    }

    for i in range(1, target_count + 1):
        # 1. Row ID
        row_id = i

        # 2. Date with Q4 holiday seasonality
        # Weight date choices to skew towards Q4 (months 10, 11, 12)
        day_offset = random.randint(0, total_days)
        order_date = start_date + datetime.timedelta(days=day_offset)
        
        # Seasonality check: boost volume in November/December
        if order_date.month in (11, 12) and random.random() < 0.4:
            # Let it stay
            pass
        elif order_date.month in (1, 2) and random.random() < 0.3:
            # Low sales in Jan/Feb, push date forward occasionally
            order_date += datetime.timedelta(days=random.randint(30, 90))
            if order_date > end_date:
                order_date = end_date

        # Ship Date: 1 to 7 days after order date
        ship_days = random.choices([1, 2, 3, 4, 5, 6, 7], weights=[0.1, 0.3, 0.3, 0.15, 0.1, 0.03, 0.02])[0]
        ship_date = order_date + datetime.timedelta(days=ship_days)

        ship_mode = random.choices(SHIP_MODES, weights=SHIP_MODE_WEIGHTS)[0]
        # Force same day ship days to 0
        if ship_mode == "Same Day":
            ship_date = order_date
        elif ship_mode == "First Class" and ship_days > 3:
            ship_date = order_date + datetime.timedelta(days=random.randint(1, 2))

        # 3. Order ID: CA-YYYY-counter
        # Re-use order IDs sometimes to simulate multiple items in one order
        if i > 1 and random.random() < 0.3:
            prev_tx = transactions[-1]
            order_id = prev_tx["Order ID"]
            order_date = datetime.datetime.strptime(prev_tx["Order Date"], "%Y-%m-%d").date()
            ship_date = datetime.datetime.strptime(prev_tx["Ship Date"], "%Y-%m-%d").date()
            ship_mode = prev_tx["Ship Mode"]
            customer = next(c for c in customers if c["customer_id"] == prev_tx["Customer ID"])
            geography = next(
                g for g in GEOGRAPHIES 
                if g[0] == prev_tx["Region"] and g[2] == prev_tx["State"] and g[3] == prev_tx["City"]
            )
        else:
            order_counter += 1
            order_id = f"CA-{order_date.year}-{order_counter}"
            customer = random.choice(customers)
            geography = random.choice(GEOGRAPHIES)

        region, country, state, city, postal_code = geography

        # 4. Product details
        product = random.choice(products)
        cat = product["category"]
        
        # 5. Financials
        min_p, max_p, cost_ratio = category_prices[cat]
        # Sales amount
        sales_base = random.uniform(min_p, max_p)
        # Quantity
        quantity = random.choices([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], weights=[0.4, 0.25, 0.15, 0.08, 0.05, 0.03, 0.02, 0.01, 0.005, 0.005])[0]
        
        # Discount (0%, 10%, 15%, 20%, 30%, 40%, 50%, 70%, 80%)
        # Heavy discounts are rarer
        discount = random.choices(
            [0.0, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.7, 0.8],
            weights=[0.60, 0.10, 0.05, 0.15, 0.04, 0.03, 0.02, 0.005, 0.005]
        )[0]

        total_sales = round(sales_base * quantity, 2)
        revenue = round(total_sales * (1.0 - discount), 2)
        
        # Cost factor including manufacturing/shipping overhead
        cost = total_sales * cost_ratio
        
        # Some random cost fluctuation to simulate profitability variances
        cost_fluctuation = random.uniform(-0.15, 0.35)
        total_cost = cost * (1.0 + cost_fluctuation)
        
        # Profit: Revenue - Cost
        profit = round(revenue - total_cost, 2)

        # Occasional data anomaly (e.g. invalid negative values or huge discount to test cleaner)
        if random.random() < 0.005:  # 0.5% anomalies
            anomaly_type = random.randint(1, 3)
            if anomaly_type == 1:
                # Negative quantity
                quantity = -random.randint(1, 5)
            elif anomaly_type == 2:
                # Invalid discount (> 100%)
                discount = 1.5
            elif anomaly_type == 3:
                # Out of order dates
                ship_date = order_date - datetime.timedelta(days=random.randint(1, 5))

        transactions.append({
            "Row ID": row_id,
            "Order ID": order_id,
            "Order Date": order_date.strftime("%Y-%m-%d"),
            "Ship Date": ship_date.strftime("%Y-%m-%d"),
            "Ship Mode": ship_mode,
            "Customer ID": customer["customer_id"],
            "Customer Name": customer["customer_name"],
            "Segment": customer["segment"],
            "Country": country,
            "City": city,
            "State": state,
            "Postal Code": postal_code,
            "Region": region,
            "Product ID": product["product_id"],
            "Category": cat,
            "Sub-Category": product["sub_category"],
            "Product Name": product["product_name"],
            "Sales": total_sales,
            "Quantity": quantity,
            "Discount": discount,
            "Profit": profit
        })
        
    return transactions


def main() -> None:
    """Entry point for CLI execution."""
    parser = argparse.ArgumentParser(description="Generate synthetic retail sales dataset.")
    parser.add_argument(
        "--output",
        type=str,
        default="data/raw/superstore_sales.csv",
        help="Target output CSV path."
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=10000,
        help="Number of transactional rows to generate."
    )
    args = parser.parse_args()

    # Create target directory
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating synthetic retail data...")
    print(f"1. Creating master customer catalog...")
    customers = generate_customers(800)
    print(f"2. Creating master product taxonomy...")
    products = generate_products(1000)
    print(f"3. Generating {args.rows} sales transactions...")
    transactions = generate_transactions(args.rows, customers, products)

    print(f"4. Saving transactions to {output_path}...")
    headers = [
        "Row ID", "Order ID", "Order Date", "Ship Date", "Ship Mode", 
        "Customer ID", "Customer Name", "Segment", "Country", "City", 
        "State", "Postal Code", "Region", "Product ID", "Category", 
        "Sub-Category", "Product Name", "Sales", "Quantity", "Discount", "Profit"
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(transactions)

    print(f"Successfully generated {len(transactions)} transactions.")


if __name__ == "__main__":
    main()
