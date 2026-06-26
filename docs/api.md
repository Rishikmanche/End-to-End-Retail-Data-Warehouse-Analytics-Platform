# REST API Documentation

This document describes the endpoints, parameters, request schemas, and sample responses of the **Retail Data Warehouse REST API**. The API is built using **FastAPI** and **Pydantic v2**.

---

## 1. Base URL & Authentication

- **Development URL**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc API Reference**: `http://localhost:8000/redoc`
- **Authentication**: None required (Internal staging/reporting network).

---

## 2. API Endpoints Reference

### A. System Health
#### `GET /health`
- **Description**: Verifies that the API service is online and the database connection is healthy.
- **Response Format**: `HealthResponse`
- **Sample JSON**:
```json
{
  "status": "healthy",
  "db_status": "healthy",
  "timestamp": "2024-06-15T12:00:00Z",
  "version": "1.0.0",
  "environment": "development"
}
```

---

### B. Executive KPIs
#### `GET /kpis`
- **Description**: Retrieves high-level aggregated performance metrics from all transaction sales.
- **Response Format**: `KPIResponse`
- **Sample JSON**:
```json
{
  "total_sales": 2297200.86,
  "total_profit": 286397.02,
  "total_orders": 5009,
  "avg_order_value": 458.62,
  "profit_margin": 0.1247,
  "total_customers": 793
}
```

---

### C. Customer Dimensions
#### `GET /customers`
- **Description**: Retrieves a paginated list of active customer records, optionally filtered by segment.
- **Query Parameters**:
  - `segment` (string, optional): Consumer, Corporate, or Home Office.
  - `page` (int, default=1): Page offset.
  - `page_size` (int, default=20): Items per page limit.
- **Response Format**: `PaginatedResponse[CustomerResponse]`
- **Sample JSON**:
```json
{
  "items": [
    {
      "customer_id": "CG-12520",
      "customer_name": "Claire Gute",
      "segment": "Consumer",
      "customer_key": 1,
      "effective_date": "2021-01-01",
      "is_current": true
    }
  ],
  "total": 793,
  "page": 1,
  "page_size": 20,
  "total_pages": 40
}
```

#### `GET /customers/{customer_id}`
- **Description**: Retrieves the active profile details of a single customer by their natural business ID.

---

### D. Product Dimensions
#### `GET /products`
- **Description**: Retrieves a paginated list of products, optionally filtered by category.
- **Query Parameters**:
  - `category` (string, optional): Technology, Furniture, or Office Supplies.
  - `page` (int, default=1)
  - `page_size` (int, default=20)
- **Response Format**: `PaginatedResponse[ProductResponse]`

---

### E. Transactions Fact Data
#### `GET /sales`
- **Description**: Retrieves a paginated list of transaction sales records with denormalized customer and product descriptors.
- **Query Parameters**:
  - `start_date` (date, optional): Filter transactions on or after YYYY-MM-DD.
  - `end_date` (date, optional): Filter transactions on or before YYYY-MM-DD.
  - `region` (string, optional): East, West, Central, South.
  - `category` (string, optional): Technology, Furniture, Office Supplies.
  - `min_sales` (float, optional): Filter transactions with sales amount >= min_sales.
  - `page` (int, default=1)
  - `page_size` (int, default=20)
- **Response Format**: `PaginatedResponse[SalesResponse]`

---

### F. Dashboard Consolidated Data
#### `GET /dashboard-data`
- **Description**: Consolidated endpoint designed to supply data for UI dashboards. Aggregates KPIs, category breakdown, regional breakdown, monthly trend, and top products.
- **Response Format**: `DashboardResponse`
- **Sample JSON**:
```json
{
  "kpis": {
    "total_sales": 2297200.86,
    "total_profit": 286397.02,
    "total_orders": 5009,
    "avg_order_value": 458.62,
    "profit_margin": 0.1247,
    "total_customers": 793
  },
  "sales_by_category": [
    { "category": "Technology", "sales": 836154.03, "profit": 145454.94 },
    { "category": "Furniture", "sales": 741999.80, "profit": 18451.27 }
  ],
  "sales_by_region": [
    { "region": "West", "sales": 725457.82, "profit": 108418.44 }
  ],
  "monthly_trend": [
    { "year": 2022, "month": 5, "month_name": "May", "sales": 56000.0, "profit": 7200.0, "orders": 120 }
  ],
  "top_products": [
    { "product_id": "TEC-CO-10004722", "product_name": "Canon Copier", "category": "Technology", "sales": 61500.00, "profit": 25000.00 }
  ]
}
```
