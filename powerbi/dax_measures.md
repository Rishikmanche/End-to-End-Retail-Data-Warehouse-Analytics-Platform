# Power BI DAX Measures Reference

This document defines **25+ production-grade DAX measures** used in the Power BI reports.

---

## 1. Core Financial Measures

### Total Gross Sales
```dax
Total Gross Sales = SUM(fact_sales[sales])
```

### Total Discount Amount
```dax
Total Discount Amount = SUMX(fact_sales, fact_sales[sales] * fact_sales[discount])
```

### Total Revenue (Net Sales)
```dax
Total Revenue = SUM(fact_sales[revenue])
```

### Total Cost
```dax
Total Cost = [Total Revenue] - [Total Profit]
```

### Total Profit
```dax
Total Profit = SUM(fact_sales[profit])
```

### Net Profit Margin
```dax
Profit Margin = DIVIDE([Total Profit], [Total Revenue], 0)
```

### Average Order Value (AOV)
```dax
Avg Order Value = DIVIDE([Total Revenue], [Total Orders], 0)
```

### Average Unit Price
```dax
Avg Unit Price = DIVIDE([Total Gross Sales], [Total Units Sold], 0)
```

---

## 2. Volume & Customer Metrics

### Total Orders
```dax
Total Orders = DISTINCTCOUNT(fact_sales[order_id])
```

### Total Units Sold
```dax
Total Units Sold = SUM(fact_sales[quantity])
```

### Total Customers
```dax
Total Customers = DISTINCTCOUNT(fact_sales[customer_key])
```

### Revenue per Customer
```dax
Revenue per Customer = DIVIDE([Total Revenue], [Total Customers], 0)
```

### Active Customer Ratio
```dax
Active Customer Ratio = 
DIVIDE(
    CALCULATE([Total Customers], fact_sales[sales] > 0),
    CALCULATE(DISTINCTCOUNT(dim_customer[customer_id]), ALL(dim_customer)),
    0
)
```

### Average Shipping Days
```dax
Average Shipping Days = 
AVERAGEX(
    fact_sales,
    RELATED(dim_date[full_date]) -- Resolves Ship Date key difference if mapped
)
```
*(Note: Alternative is averaging `fact_sales[ship_date_key] - fact_sales[order_date_key]` in data model).*

---

## 3. Time Intelligence (MTD, QTD, YTD)

### Revenue Month-to-Date (MTD)
```dax
Revenue MTD = TOTALMTD([Total Revenue], dim_date[full_date])
```

### Revenue Quarter-to-Date (QTD)
```dax
Revenue QTD = TOTALQTD([Total Revenue], dim_date[full_date])
```

### Revenue Year-to-Date (YTD)
```dax
Revenue YTD = TOTALYTD([Total Revenue], dim_date[full_date])
```

### Prior Year Revenue
```dax
Prior Year Revenue = CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(dim_date[full_date]))
```

### Year-over-Year (YoY) Revenue Growth
```dax
YoY Revenue Growth = 
DIVIDE(
    [Total Revenue] - [Prior Year Revenue],
    [Prior Year Revenue],
    0
)
```

### Prior Month Revenue
```dax
Prior Month Revenue = CALCULATE([Total Revenue], DATEADD(dim_date[full_date], -1, MONTH))
```

### Month-over-Month (MoM) Revenue Growth
```dax
MoM Revenue Growth = 
DIVIDE(
    [Total Revenue] - [Prior Month Revenue],
    [Prior Month Revenue],
    0
)
```

---

## 4. Advanced Analytical Measures

### Average Discount Rate
```dax
Avg Discount = AVERAGE(fact_sales[discount])
```

### Product Sales Ranking
```dax
Product Sales Rank = RANKX(ALL(dim_product), [Total Revenue], , DESC)
```

### Customer Lifetime Value (LTV)
```dax
Customer Lifetime Value = 
CALCULATE(
    [Total Revenue],
    ALLEXCEPT(dim_customer, dim_customer[customer_id])
)
```

### Customer Retention Rate
```dax
Customer Retention Rate = 
VAR CurrentCustomers = VALUES(fact_sales[customer_key])
VAR PriorPeriodCustomers = 
    CALCULATE(
        VALUES(fact_sales[customer_key]),
        DATEADD(dim_date[full_date], -1, YEAR)
    )
VAR RetainedCustomers = INTERSECT(CurrentCustomers, PriorPeriodCustomers)
RETURN
    DIVIDE(COUNTROWS(RetainedCustomers), COUNTROWS(PriorPeriodCustomers), 0)
```
