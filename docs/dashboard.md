# Power BI Dashboard Documentation

This document describes the structure, visualizations, DAX measures, and data modeling definitions for the **Retail Sales Analytics Power BI Dashboards**. The platform is designed to look like a premium, internal corporate BI system.

---

## 1. Data Model & Relationships

The Power BI data model follows a strict **Star Schema** matching the PostgreSQL warehouse design:

- **Central Fact Table**: `fact_sales`
- **Dimension Tables** (joined via 1-to-many relationship, single direction filter):
  - `dim_customer` (joined on `customer_key`)
  - `dim_product` (joined on `product_key`)
  - `dim_region` (joined on `region_key`)
  - `dim_category` (joined on `category_key`)
  - `dim_date` (active relationship on `order_date_key` to `date_key`, inactive relationship on `ship_date_key` to `date_key`)

---

## 2. Dashboard Pages Layout

The report is split into five distinct functional areas:

### Page 1: Executive KPI Overview
- **Objective**: Expose high-level performance metrics to C-suite executives.
- **Visuals**:
  - **KPI Cards**: Net Revenue, Net Profit, Total Orders, Total Customers, Average Order Value (AOV).
  - **Line Chart**: Net Revenue & Profit trend over months (with 3-month moving average).
  - **Donut Chart**: Revenue breakdown by Category.
  - **Bar Chart**: Regional sales comparison (East vs West vs Central vs South).
  - **Slicers**: Year, Region, Segment.

### Page 2: Regional Performance & Map
- **Objective**: Identify geographic performance clusters and logistics efficiency.
- **Visuals**:
  - **Map Visual**: Bubble map showing sales volume by City/State. Bubble size represents Revenue, color represents Profit Margin (red for loss, green for profitable).
  - **Bar Chart**: Top 10 States by Profit.
  - **Matrix Table**: Expandable hierarchy Country > Region > State > City showing Sales, Quantity, Profit, and average shipping days.

### Page 3: Customer Analytics & Segmentation
- **Objective**: Drill down into customer tier profiles, segments, and value.
- **Visuals**:
  - **TreeMap**: Customer distribution by RFM Segments (Champions, Loyal, At Risk, Lost).
  - **Table Grid**: Top 50 Customers showing Lifetime Value (LTV), total orders, and average profit margin.
  - **Bar Chart**: Segment purchase trends (Consumer vs Corporate vs Home Office).

### Page 4: Product Performance
- **Objective**: Audit product margins, sub-categories, and discounts.
- **Visuals**:
  - **Bar Chart**: Top 10 best-selling products by revenue.
  - **Scatter Plot**: Product quantity sold vs discount rate. Helps identify if steep discounts increase unit volume at the expense of margin.
  - **Waterfall Chart**: Profit breakdown by Sub-Category.

### Page 5: Time Series & Forecasting
- **Objective**: Review historical trends and project future sales.
- **Visuals**:
  - **Line Chart**: Sales and profit projections over the next 6 months (using Power BI's built-in exponential smoothing forecast).
  - **Matrix Grid**: Year-over-Year (YoY) revenue comparison by Quarter and Month.
  - **Bar Chart**: Sales volume by Day of the Week.
