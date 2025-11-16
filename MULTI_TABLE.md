# Multi-Table Data Handling

This document describes advanced multi-table functionality for working with multiple data sources.

## Overview

The multi-table feature supports two modes:

1. **Direct Access Mode** (no SQL): Load multiple files and access each via `data.table_name`
2. **SQL Query Mode**: Combine CSV/TSV files using SQL JOIN operations

Both modes are useful for different scenarios.

## Mode 1: Direct Access (Without SQL)

Load multiple files and access each dataset independently via `data.table_name`.

### Syntax

```yaml
data:
  config: config.yaml
  sales: sales.csv
---
# {{ data.config.title }}
{% for row in data.sales %}
- {{ row.date }}: {{ row.amount }}
{% endfor %}
```

**Use cases:**
- Separating configuration from data
- Loading metadata alongside data
- Accessing multiple datasets independently

**Supported formats:** All formats (CSV, TSV, JSON, YAML, TOML, SQLite, etc.)

### Example: Configuration + Data

**config.yaml:**
```yaml
title: "2024 Sales Report"
subtitle: "Q1 Results"
author: "John Doe"
```

**sales.csv:**
```csv
date,amount,product
2024-01-15,1280,Widget
2024-01-16,2480,Gadget
```

**Usage:**
````markdown
```embedz
---
data:
  config: config.yaml
  sales: sales.csv
---
# {{ data.config.title }}
## {{ data.config.subtitle }}

By {{ data.config.author }}

{% for row in data.sales %}
- {{ row.date }}: ¥{{ "{:,}".format(row.amount|int) }} ({{ row.product }})
{% endfor %}
```
````

**Output:**
```
# 2024 Sales Report
## Q1 Results

By John Doe

- 2024-01-15: ¥1,280 (Widget)
- 2024-01-16: ¥2,480 (Gadget)
```

## Mode 2: SQL Query (With SQL)

Combine CSV/TSV files using SQL JOIN operations for complex data processing.

### Syntax

```yaml
data:
  table1: file1.csv
  table2: file2.csv
query: |
  SELECT ...
  FROM table1 t1
  JOIN table2 t2 ON ...
```

**Key points:**
- Specify `data:` as a dictionary where keys are table names for SQL
- A `query:` parameter enables SQL mode
- **Supported formats for SQL mode:** CSV, TSV, and SSV only (tabular data)

## Understanding Data Flow

How the `data` variable works depends on whether you use SQL or not:

### Without SQL Query (Direct Access)

```yaml
data:
  config: config.yaml      # Accessed as data.config
  sales: sales.csv         # Accessed as data.sales
---
{% for row in data.sales %}  # Access via data.table_name
```

**Data structure:** `data` is a dictionary: `{config: {...}, sales: [...]}`

### With SQL Query

```yaml
data:
  products: products.csv   # Key becomes SQL table name
  sales: sales.csv         # Key becomes SQL table name
query: |
  SELECT ...
  FROM sales s             # Use table names in SQL
  JOIN products p ...
---
{% for row in data %}      # Query result is a list
```

**Data structure:** `data` is a list of query results: `[{...}, {...}, ...]`

**Key concept:**
1. **Without query**: `data` = dict, access via `data.table_name`
2. **With query**: `data` = list, keys are used as SQL table names
3. Consistent with single-file mode where `data` is always the result

## Data Setup

### products.csv
```csv
product_id,product_name,price
1,Widget,1280
2,Gadget,2480
3,Doohickey,1850
```

### sales.csv
```csv
sale_id,product_id,quantity,date
101,1,5,2024-01-15
102,2,3,2024-01-15
103,1,2,2024-01-15
104,3,10,2024-01-16
105,1,3,2024-01-16
106,2,1,2024-01-17
107,3,5,2024-01-17
108,1,4,2024-01-17
```

## Example 1: Daily Sales Summary

````markdown
```embedz
---
data:
  products: products.csv
  sales: sales.csv
query: |
  SELECT
    s.date,
    COUNT(*) as transaction_count,
    SUM(s.quantity) as total_items,
    SUM(s.quantity * p.price) as daily_revenue
  FROM sales s
  JOIN products p ON s.product_id = p.product_id
  GROUP BY s.date
  ORDER BY s.date
---
## Daily Sales

| Date | Transactions | Items | Revenue |
|------|--------------|-------|---------|
{% for row in data -%}
| {{ row.date }} | {{ row.transaction_count }} | {{ row.total_items }} | ¥{{ "{:,}".format(row.daily_revenue|int) }} |
{% endfor -%}
```
````

**Output:**
```
| Date | Transactions | Items | Revenue |
|------|--------------|-------|---------|
| 2024-01-15 | 3 | 10 | ¥16,400 |
| 2024-01-16 | 2 | 13 | ¥22,340 |
| 2024-01-17 | 3 | 10 | ¥16,110 |
```

## Example 2: Product Sales Ranking

````markdown
```embedz
---
data:
  products: products.csv
  sales: sales.csv
query: |
  SELECT
    p.product_name,
    p.price,
    COUNT(*) as times_ordered,
    SUM(s.quantity) as total_quantity,
    ROUND(AVG(s.quantity), 1) as avg_quantity,
    SUM(s.quantity * p.price) as total_revenue
  FROM sales s
  JOIN products p ON s.product_id = p.product_id
  GROUP BY p.product_id
  ORDER BY total_revenue DESC
---
## Product Performance

| Rank | Product | Price | Orders | Units Sold | Avg Qty | Revenue |
|------|---------|-------|--------|------------|---------|---------|
{% for row in data -%}
| {{ loop.index }} | {{ row.product_name }} | ¥{{ "{:,}".format(row.price|int) }} | {{ row.times_ordered }} | {{ row.total_quantity }} | {{ row.avg_quantity }} | ¥{{ "{:,}".format(row.total_revenue|int) }} |
{% endfor -%}
```
````

**Output:**
```
| Rank | Product | Price | Orders | Units Sold | Avg Qty | Revenue |
|------|---------|-------|--------|------------|---------|---------|
| 1 | Doohickey | ¥1,850 | 2 | 15 | 7.5 | ¥27,750 |
| 2 | Widget | ¥1,280 | 4 | 14 | 3.5 | ¥17,920 |
| 3 | Gadget | ¥2,480 | 2 | 4 | 2.0 | ¥9,920 |
```

## Example 3: Product-by-Date Breakdown

````markdown
```embedz
---
data:
  products: products.csv
  sales: sales.csv
query: |
  SELECT
    s.date,
    p.product_name,
    COUNT(*) as order_count,
    SUM(s.quantity) as quantity,
    SUM(s.quantity * p.price) as revenue
  FROM sales s
  JOIN products p ON s.product_id = p.product_id
  GROUP BY s.date, p.product_name
  ORDER BY s.date, revenue DESC
---
## Daily Product Breakdown

{% for row in data %}
- **{{ row.date }}** - {{ row.product_name }}: {{ row.order_count }} orders ({{ row.quantity }} units) = ¥{{ "{:,}".format(row.revenue|int) }}
{% endfor %}
```
````

**Output:**
```
- **2024-01-15** - Gadget: 1 orders (3 units) = ¥7,440
- **2024-01-15** - Widget: 2 orders (7 units) = ¥8,960
- **2024-01-16** - Doohickey: 1 orders (10 units) = ¥18,500
- **2024-01-16** - Widget: 1 orders (3 units) = ¥3,840
- **2024-01-17** - Doohickey: 1 orders (5 units) = ¥9,250
- **2024-01-17** - Widget: 1 orders (4 units) = ¥5,120
- **2024-01-17** - Gadget: 1 orders (1 units) = ¥2,480
```

## Example 4: High-Value Transactions

````markdown
```embedz
---
data:
  products: products.csv
  sales: sales.csv
query: |
  SELECT
    s.sale_id,
    s.date,
    p.product_name,
    s.quantity,
    p.price,
    (s.quantity * p.price) as amount
  FROM sales s
  JOIN products p ON s.product_id = p.product_id
  WHERE (s.quantity * p.price) >= 10000
  ORDER BY amount DESC
---
## High-Value Transactions (¥10,000+)

{% for row in data %}
- **Order #{{ row.sale_id }}** ({{ row.date }})
  - Product: {{ row.product_name }}
  - Quantity: {{ row.quantity }} × ¥{{ "{:,}".format(row.price|int) }}
  - **Amount: ¥{{ "{:,}".format(row.amount|int) }}**
{% endfor %}
```
````

## Example 5: Three-Table Join (Customers + Orders + Products)

### Additional Data File

**customers.csv**:
```csv
customer_id,customer_name,region
1,Yamada Store,Tokyo
2,Suzuki Trading,Osaka
3,Tanaka Corp,Nagoya
```

Update **sales.csv** to include customer_id:
```csv
sale_id,customer_id,product_id,quantity,date
101,1,1,5,2024-01-15
102,1,2,3,2024-01-15
103,2,1,2,2024-01-15
104,2,3,10,2024-01-16
105,3,1,3,2024-01-16
106,1,2,1,2024-01-17
107,3,3,5,2024-01-17
108,2,1,4,2024-01-17
```

````markdown
```embedz
---
data:
  customers: customers.csv
  orders: sales.csv
  products: products.csv
query: |
  SELECT
    c.customer_name,
    c.region,
    COUNT(o.sale_id) as order_count,
    SUM(o.quantity * p.price) as total_spent
  FROM orders o
  JOIN customers c ON o.customer_id = c.customer_id
  JOIN products p ON o.product_id = p.product_id
  GROUP BY c.customer_id
  ORDER BY total_spent DESC
---
## Customer Purchase Summary

| Customer | Region | Orders | Total Spent |
|----------|--------|--------|-------------|
{% for row in data -%}
| {{ row.customer_name }} | {{ row.region }} | {{ row.order_count }} | ¥{{ "{:,}".format(row.total_spent|int) }} |
{% endfor -%}
```
````

## Example 6: Regional Analysis

````markdown
```embedz
---
data:
  customers: customers.csv
  orders: sales.csv
  products: products.csv
query: |
  SELECT
    c.region,
    COUNT(DISTINCT c.customer_id) as customer_count,
    COUNT(o.sale_id) as order_count,
    SUM(o.quantity * p.price) as total_sales
  FROM orders o
  JOIN customers c ON o.customer_id = c.customer_id
  JOIN products p ON o.product_id = p.product_id
  GROUP BY c.region
  ORDER BY total_sales DESC
---
## Regional Sales Report

| Region | Customers | Orders | Sales |
|--------|-----------|--------|-------|
{% for row in data -%}
| {{ row.region }} | {{ row.customer_count }} | {{ row.order_count }} | ¥{{ "{:,}".format(row.total_sales|int) }} |
{% endfor -%}
```
````

## Common Use Cases

### 1. Period-Based Reports (Quarterly/Annual)

```sql
WHERE date BETWEEN '2024-01-01' AND '2024-03-31'
```

Use for:
- Quarterly reports
- Year-over-year comparisons
- Monthly trend analysis

### 2. Inventory Management

```sql
SELECT
  p.product_name,
  p.stock_quantity,
  COALESCE(SUM(s.quantity), 0) as sold,
  (p.stock_quantity - COALESCE(SUM(s.quantity), 0)) as remaining
FROM products p
LEFT JOIN sales s ON p.product_id = s.product_id
GROUP BY p.product_id
```

### 3. Customer Lifetime Value

```sql
SELECT
  c.customer_name,
  COUNT(o.order_id) as order_count,
  AVG(o.quantity * p.price) as avg_order_value,
  SUM(o.quantity * p.price) as lifetime_value
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN products p ON o.product_id = p.product_id
GROUP BY c.customer_id
HAVING lifetime_value > 100000
ORDER BY lifetime_value DESC
```

### 4. Top Products Analysis

```sql
SELECT
  p.product_name,
  p.category,
  SUM(s.quantity) as units_sold,
  SUM(s.quantity * p.price) as revenue
FROM sales s
JOIN products p ON s.product_id = p.product_id
WHERE s.date >= '2024-01-01'
GROUP BY p.product_id
ORDER BY revenue DESC
LIMIT 10
```

### 5. Week-over-Week Comparison

```sql
SELECT
  CASE
    WHEN s.date < '2024-01-16' THEN 'Week 1'
    ELSE 'Week 2'
  END as week,
  p.product_name,
  SUM(s.quantity) as quantity,
  SUM(s.quantity * p.price) as revenue
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY week, p.product_name
ORDER BY week, revenue DESC
```

## SQL Tips

### Table Aliases
Use short aliases to make queries more readable:
```sql
FROM sales s
JOIN products p ON s.product_id = p.product_id
```

### Aggregation Functions
Common functions:
- `COUNT(*)` - Count rows
- `SUM(column)` - Sum values
- `AVG(column)` - Average values
- `MIN(column)` - Minimum value
- `MAX(column)` - Maximum value
- `ROUND(value, decimals)` - Round numbers

### Filtering
- `WHERE` - Filter before grouping
- `HAVING` - Filter after grouping

Example:
```sql
SELECT category, SUM(amount) as total
FROM sales
WHERE date >= '2024-01-01'
GROUP BY category
HAVING total > 10000
```

## Limitations

1. **Format Support**: Only CSV, TSV, and SSV formats are supported for multi-table queries
2. **Memory**: All tables are loaded into memory - not suitable for very large datasets (>100K rows per table)
3. **Query Required**: The `query:` parameter is mandatory for multi-table mode
4. **SQLite Syntax**: Uses SQLite SQL dialect

## Backward Compatibility

The multi-table feature is fully backward compatible:

| Single-file (original) | Multi-table (new) |
|------------------------|-------------------|
| `data: file.csv` | `data: {t1: a.csv, t2: b.csv}` |
| Table name is always `data` | Table names are dictionary keys |
| `query: SELECT * FROM data WHERE...` | `query: SELECT * FROM t1 JOIN t2...` |

All existing single-file documents continue to work without modification.

## Performance Considerations

- Uses in-memory SQLite database (pandas → SQLite)
- Efficient for small to medium datasets (< 100K rows)
- For larger datasets, consider:
  - Using native SQLite database files (`.db` format)
  - Pre-processing data with separate tools
  - Splitting reports into smaller queries

## See Also

- [README.md](README.md) - Main documentation with basic usage and single-file SQL queries
- [COMPARISON.md](COMPARISON.md) - Comparison with other Pandoc filters and tools
- [Pandoc documentation](https://pandoc.org/MANUAL.html) - Pandoc user manual
- [Jinja2 documentation](https://jinja.palletsprojects.com/) - Template syntax reference
