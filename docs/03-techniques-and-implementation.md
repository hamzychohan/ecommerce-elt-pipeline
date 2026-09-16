# Techniques & Implementation

This document explains **which techniques** the pipeline uses, **why** they matter, and **how** they are implemented in this project.

---

## 1. ELT vs ETL

| Pattern | Order | When Used Here |
|---------|-------|----------------|
| **ETL** | Extract → Transform → Load | Legacy; transform before warehouse |
| **ELT** | Extract → Load → Transform | **This project** — load raw to S3, transform in dbt inside the warehouse |

**Implementation:** Python only extracts and lands data. All business rules live in dbt SQL running on Redshift/DuckDB.

---

## 2. Medallion / Layered Modeling

**Technique:** Separate raw, cleaned, enriched, and business-ready data into distinct layers.

**Implementation:**

```
sources (raw) → stg_* → int_* → mart_*
```

| Layer | Prefix | Materialization | Example |
|-------|--------|-----------------|---------|
| Staging | `stg_` | view | `stg_orders` |
| Intermediate | `int_` | view/table | `int_customer_orders` |
| Mart | `mart_` | table | `mart_revenue_daily` |

**Problem it solves:** Changes in raw API shape are isolated in staging; marts stay stable for BI.

---

## 3. Common Table Expressions (CTEs)

**Technique:** Break complex SQL into named, readable steps instead of nested subqueries.

**Why:** Easier debugging, testability, and code review in analytics engineering.

**Implementation example — enriched order lines:**

```sql
-- models/intermediate/int_order_lines_enriched.sql
with orders as (
    select * from {{ ref('stg_orders') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

line_items as (
    select
        o.order_id,
        o.customer_id,
        o.order_date,
        li.product_id,
        li.quantity,
        p.unit_price
    from orders o
    cross join unnest(o.line_items) as li(product_id, quantity)  -- or join to stg_order_lines
    left join products p on li.product_id = p.product_id
),

enriched as (
    select
        *,
        quantity * unit_price as line_revenue
    from line_items
)

select * from enriched
```

**Best practices used:**

- One CTE per logical step
- Final `select * from enriched` for clear output
- No business logic hidden in JOIN conditions

---

## 4. Jinja Templating in dbt

**Technique:** Parameterize SQL with Jinja so models are DRY and environment-aware.

### 4.1 `ref()` and `source()`

```sql
select * from {{ ref('stg_orders') }}
select * from {{ source('raw', 'orders') }}
```

**Purpose:** Dependency graph, lineage, and correct build order.

### 4.2 Config Blocks

```sql
{{ config(
    materialized='table',
    tags=['daily', 'mart']
) }}
```

**Purpose:** Control materialization and selective runs (`dbt run --select tag:daily`).

### 4.3 Macros for Reusable Logic

```sql
-- macros/cents_to_dollars.sql
{% macro cents_to_dollars(column_name) %}
    ({{ column_name }} / 100.0)::decimal(18, 2)
{% endmacro %}
```

Usage in a model:

```sql
select
    order_id,
    {{ cents_to_dollars('amount_cents') }} as order_total
from {{ ref('stg_orders') }}
```

### 4.4 Conditional Logic for Multi-Warehouse

```sql
{% if target.type == 'duckdb' %}
    read_parquet('s3://bucket/raw/orders/*.parquet')
{% elif target.type == 'redshift' %}
    {{ source('raw', 'orders') }}
{% endif %}
```

**Purpose:** Same project runs locally (DuckDB) and in production (Redshift).

### 4.5 Variables for Business Rules

```yaml
# dbt_project.yml
vars:
  churn_inactive_days: 90
  revenue_statuses: ['completed', 'shipped']
```

```sql
-- in int_customer_churn.sql
where days_since_last_order > {{ var('churn_inactive_days') }}
```

**Purpose:** Change churn definition without editing SQL in multiple files.

---

## 5. dbt Tests

**Technique:** Assert data quality as code in the pipeline.

### 5.1 Schema Tests (YAML)

```yaml
models:
  - name: stg_orders
    columns:
      - name: order_id
        tests:
          - unique
          - not_null
      - name: customer_id
        tests:
          - not_null
          - relationships:
              to: ref('stg_customers')
              field: customer_id
```

### 5.2 Singular Tests (Custom SQL)

```sql
-- tests/assert_revenue_non_negative.sql
select *
from {{ ref('mart_order_lines') }}
where line_revenue < 0
```

Returns failing rows → test fails.

### 5.3 Generic Tests via Macros

```sql
-- macros/test_valid_status.sql
{% test valid_status(model, column_name, valid_values) %}
select *
from {{ model }}
where {{ column_name }} not in ({{ valid_values | join(', ') }})
{% endtest %}
```

### Test Strategy for This Project

| Layer | Tests |
|-------|-------|
| Staging | `unique`, `not_null` on PKs |
| Intermediate | Relationships, accepted values |
| Marts | Custom SQL for revenue ≥ 0, churn flags in (0,1) |

**Run:** `dbt test` after every `dbt run`.

---

## 6. Incremental Models (Optional)

**Technique:** Process only new/changed rows on large fact tables.

```sql
{{ config(
    materialized='incremental',
    unique_key='order_id'
) }}

select * from {{ ref('int_orders') }}

{% if is_incremental() %}
where order_date > (select max(order_date) from {{ this }})
{% endif %}
```

**When to use:** High-volume orders table in Redshift; skip for small mock datasets.

---

## 7. Semantic Metrics

**Technique:** Define business KPIs once, reference everywhere.

### Revenue Implementation

```sql
-- models/marts/mart_revenue_daily.sql
select
    order_date,
    count(distinct order_id) as order_count,
    sum(order_total) as gross_revenue
from {{ ref('mart_orders') }}
where order_status in {{ var('revenue_statuses') }}
group by 1
```

### Churn Implementation

```sql
-- models/marts/mart_customer_churn_monthly.sql
with activity as (
    select * from {{ ref('int_customer_activity') }}
),

monthly as (
    select
        date_trunc('month', snapshot_date) as month,
        customer_id,
        case
            when days_since_last_order > {{ var('churn_inactive_days') }}
                 and was_active_prior_period
            then 1 else 0
        end as is_churned
    from activity
)

select
    month,
    sum(is_churned) as churned_customers,
    count(*) as cohort_size,
    sum(is_churned)::float / nullif(count(*), 0) as churn_rate
from monthly
group by 1
```

### dbt Metrics YAML (Optional)

```yaml
metrics:
  - name: gross_revenue
    label: Gross Revenue
    model: ref('mart_revenue_daily')
    calculation_method: sum
    expression: gross_revenue
    timestamp: order_date
    time_grains: [day, week, month]
```

---

## 8. Python Extraction Patterns

| Technique | Implementation |
|-----------|----------------|
| **Pagination** | Loop until empty page or `next` link is null |
| **Retries** | `tenacity` or manual exponential backoff on 429/5xx |
| **Idempotent writes** | UUID batch keys; never overwrite same key |
| **Schema evolution** | Store raw JSON; parse in dbt staging |
| **Secrets** | `boto3` + env vars / IAM roles, not hardcoded keys |

---

## 9. S3 Partitioning

**Technique:** Hive-style partitions for efficient scans and lifecycle policies.

```
raw/orders/ingestion_date=2025-06-25/batch-abc.json
```

**Benefits:**

- Re-run extract for one day without touching others
- dbt/sources can filter `where ingestion_date = '{{ run_date }}'`
- S3 lifecycle rules archive old partitions

---

## 10. Lineage and Documentation

**Technique:** Auto-generate DAG and column docs from dbt.

```yaml
models:
  - name: mart_revenue_daily
    description: Daily gross revenue from completed e-commerce orders
    columns:
      - name: gross_revenue
        description: Sum of order totals excluding cancelled orders
```

**Command:** `dbt docs generate` → interactive lineage graph.

---

## Technique Summary Table

| Technique | Where | Problem Solved |
|-----------|-------|----------------|
| ELT | Whole pipeline | Scale transforms in warehouse |
| Medallion layers | dbt folders | Maintainability |
| CTEs | `int_*` models | Readable complex SQL |
| Jinja `ref`/`source` | All models | Dependencies & lineage |
| Jinja macros | `macros/` | DRY transformations |
| Jinja `var()` | Project vars | Configurable business rules |
| Schema tests | `_schema.yml` | PK/FK integrity |
| Singular tests | `tests/` | Custom business rules |
| Incremental models | Large facts | Performance |
| Semantic metrics | Marts + YAML | Consistent KPIs |
| S3 partitioning | Raw layer | Efficient ingest & replay |

Next: [Tools Stack](04-tools-stack.md)
