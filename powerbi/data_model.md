# Power BI Data Model Documentation

This document describes the data model configuration, table relationships, metadata, and security settings inside Power BI.

---

## 1. Connection Configurations

- **Data Source**: PostgreSQL Database (DirectQuery or Import Mode).
- **Server**: `localhost:5432` (or AWS RDS production endpoints).
- **Database**: `retail_warehouse`
- **Tables Imported**:
  - `dim_customer`
  - `dim_product`
  - `dim_region`
  - `dim_date`
  - `dim_category`
  - `fact_sales`
  - Views: `vw_customer_segmentation`, `vw_sales_trends`, `vw_profitability_analysis`

*Recommendation: Import Mode is preferred for time intelligence features and complex DAX performance. DirectQuery is used if near-real-time updates are required.*

---

## 2. Table Relationships

| From (Dimension) | To (Fact) | Join Column | Cardinality | Cross Filter Direction | Active |
|------------------|-----------|-------------|-------------|------------------------|--------|
| `dim_customer` | `fact_sales` | `customer_key` | 1-to-Many (`1:*`) | Single | Yes |
| `dim_product` | `fact_sales` | `product_key` | 1-to-Many (`1:*`) | Single | Yes |
| `dim_region` | `fact_sales` | `region_key` | 1-to-Many (`1:*`) | Single | Yes |
| `dim_category` | `fact_sales` | `category_key` | 1-to-Many (`1:*`) | Single | Yes |
| `dim_date` | `fact_sales` | `order_date_key` | 1-to-Many (`1:*`) | Single | Yes |
| `dim_date` | `fact_sales` | `ship_date_key` | 1-to-Many (`1:*`) | Single | No (Use USERELATIONSHIP in DAX) |

---

## 3. Metadata & Formatting

- **Data Types Coercion**:
  - All currency columns (`sales`, `revenue`, `profit`) formatted as `$#,##0.00`.
  - All dates (`dim_date[full_date]`) formatted as `YYYY-MM-DD`.
  - Percentages (`discount`, `profit_margin`) formatted as `0.0%`.
- **Default Summarization**:
  - Set default summarization to **None** on all surrogate keys (`*_key`) and natural keys (`*_id`) to avoid meaningless sums.
  - Set default summarization to **Sum** on `sales`, `revenue`, `profit`, and `quantity`.

---

## 4. Row-Level Security (RLS)

To secure data based on regional structures (e.g., Regional Sales Managers should only see data for their regions):

1. **Role: `East Manager`**
   - Filter Expression on `dim_region`:
     ```dax
     [region] = "East"
     ```
2. **Role: `West Manager`**
   - Filter Expression on `dim_region`:
     ```dax
     [region] = "West"
     ```
3. **Role: `Central Manager`**
   - Filter Expression on `dim_region`:
     ```dax
     [region] = "Central"
     ```
4. **Role: `South Manager`**
   - Filter Expression on `dim_region`:
     ```dax
     [region] = "South"
     ```

---

## 5. Incremental Refresh Configuration

For enterprise scale (millions of rows in `fact_sales`):

- **Store rows where `order_date` is in the last**: 5 Years.
- **Refresh rows where `order_date` is in the last**: 3 Months.
- **Detect data changes**: Use `updated_at` column in `fact_sales`. Power BI will only refresh partitions where the maximum value of `updated_at` has changed.
- **Only refresh complete periods**: Enabled (prevents partial day updates from locking partitions).
