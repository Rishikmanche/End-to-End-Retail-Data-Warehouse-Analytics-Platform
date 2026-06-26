# Power BI Dashboard Specification

This document details the configuration specifications for the **5 Power BI Dashboards** designed to hook directly into the PostgreSQL Star Schema.

---

## Theme & Visual Styling
- **Background**: Dark Glassmorphism / Dark Mode theme.
  - Primary Background: `#0B0F19` (Deep Obsidian Blue)
  - Card/Visual Backgrounds: `#171E2E` (Semi-transparent Slate, 8% Blur)
  - Borders: `#2D3748` (Slate Grey, 1px Solid, 8px rounded corners)
- **Palette**:
  - Accent/Primary: `#6366F1` (Indigo Neon)
  - Secondary/Revenue: `#3B82F6` (Electric Blue)
  - Success/Profit: `#10B981` (Vibrant Emerald)
  - Warning/Loss: `#EF4444` (Vibrant Red)
  - Text: `#F3F4F6` (Near White) and `#9CA3AF` (Muted Grey)
- **Typography**:
  - Headers: **Outfit** or **Segoe UI Bold**
  - Body Text: **Inter** or **Segoe UI**

---

## Page-by-Page Specifications

### Page 1: Executive KPI Overview
- **Name**: `Executive Summary`
- **Grid Layout**: 4 columns, 3 rows.
- **Visuals**:
  1. **Net Revenue Card**:
     - Visual Type: Card
     - Value: `[Total Revenue]` (DAX)
     - Formatting: Font size 36, Segoe Bold, color `#3B82F6`. Display units: Auto.
  2. **Net Profit Card**:
     - Visual Type: Card
     - Value: `[Total Profit]` (DAX)
     - Formatting: Color `#10B981`.
  3. **Order Volume Card**:
     - Visual Type: Card
     - Value: `[Total Orders]` (DAX)
  4. **AOV Card**:
     - Visual Type: Card
     - Value: `[Avg Order Value]` (DAX)
  5. **Monthly Revenue & Profit Trend**:
     - Visual Type: Line and Clustered Column Chart
     - X-Axis: `dim_date[month_name]` (Sorted by Month Number)
     - Column Values: `[Total Revenue]`
     - Line Values: `[Total Profit]`
     - Formatting: Column color `#3B82F6`, Line color `#10B981`, stroke width 3.
  6. **Sales by Category**:
     - Visual Type: Donut Chart
     - Legend: `dim_category[category_name]`
     - Values: `[Total Revenue]`
     - Formatting: Furniture: `#6366F1`, Office Supplies: `#3B82F6`, Technology: `#10B981`.
  7. **Regional Comparison**:
     - Visual Type: Clustered Bar Chart
     - Y-Axis: `dim_region[region]`
     - X-Axis: `[Total Revenue]`
- **Global Slicers**: `dim_date[year]` (Dropdown), `dim_region[region]` (Multi-select list).

---

### Page 2: Regional Performance & Map
- **Name**: `Regional Sales & Logistics`
- **Visuals**:
  1. **Geographic Distribution Map**:
     - Visual Type: Azure Map (or Bubble Map)
     - Location: `dim_region[city]` + `dim_region[state]`
     - Bubble Size: `[Total Revenue]`
     - Bubble Color (Conditional): Based on `[Profit Margin]` metric (Diverging scale: red `#EF4444` at -10%, grey `#9CA3AF` at 0%, green `#10B981` at 20%+).
  2. **Top States by Profit Margin**:
     - Visual Type: Clustered Column Chart
     - X-Axis: `dim_region[state]`
     - Y-Axis: `[Profit Margin]`
     - Filters: Top 10 States by Profit Margin.
  3. **Performance Hierarchy Matrix**:
     - Visual Type: Matrix
     - Rows: `dim_region[region]` > `dim_region[state]` > `dim_region[city]`
     - Columns: Values only
     - Values: `[Total Revenue]`, `[Total Profit]`, `[Total Orders]`, `[Shipping Days]` (Average of Ship Date - Order Date)

---

### Page 3: Customer Analytics & Segmentation
- **Name**: `Customer Intelligence`
- **Visuals**:
  1. **RFM Segments Matrix**:
     - Visual Type: TreeMap
     - Group: `vw_customer_segmentation[customer_rfm_segment]`
     - Values: `[Total Customers]`
     - Tooltip: Total Revenue, Average RFM Score.
  2. **Top Customers grid**:
     - Visual Type: Table
     - Columns: `dim_customer[customer_name]`, `[Total Revenue]`, `[Total Orders]`, `[Profit Margin]`
     - Sort: `[Total Revenue]` Descending.
  3. **Segment Contribution**:
     - Visual Type: Donut Chart
     - Legend: `dim_customer[segment]`
     - Values: `[Total Revenue]`

---

### Page 4: Product Performance
- **Name**: `Product & Margin Analysis`
- **Visuals**:
  1. **Top Products by Revenue**:
     - Visual Type: Clustered Bar Chart
     - Y-Axis: `dim_product[product_name]`
     - X-Axis: `[Total Revenue]`
     - Filter: Top 10 Products by Total Revenue.
  2. **Waterfall Profit Contribution**:
     - Visual Type: Waterfall Chart
     - Category: `dim_category[sub_category]`
     - Y-Axis: `[Total Profit]`
     - Formatting: Increase color `#10B981`, Decrease color `#EF4444`.
  3. **Discounts vs Profitability Scatter**:
     - Visual Type: Scatter Chart
     - Details: `dim_product[product_name]`
     - X-Axis: `[Avg Discount]` (Average of discount in fact_sales)
     - Y-Axis: `[Profit Margin]`
     - Size: `[Total Revenue]`

---

### Page 5: Time Series Trends & Forecasting
- **Name**: `Sales Trends & Forecasting`
- **Visuals**:
  1. **Revenue Forecast Line**:
     - Visual Type: Line Chart
     - X-Axis: `dim_date[full_date]` (aggregated by Month/Year)
     - Y-Axis: `[Total Revenue]`
     - Forecast Option: Enabled (Forecast length: 6 months, Confidence interval: 95%, Seasonality: 12 months).
  2. **Year-over-Year Comparative Matrix**:
     - Visual Type: Matrix
     - Rows: `dim_date[quarter]` > `dim_date[month_name]`
     - Columns: `dim_date[year]`
     - Values: `[Total Revenue]`, `[YoY Revenue Growth]` (DAX)
