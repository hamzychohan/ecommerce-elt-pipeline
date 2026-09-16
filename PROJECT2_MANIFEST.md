# project2 — File Manifest (41 files)

All project files live in: `/Users/default/Desktop/project2`

## Root (4)
- README.md
- requirements.txt
- .env.example
- .env

## docs/ (5)
- docs/01-architecture-overview.md
- docs/02-workflow.md
- docs/03-techniques-and-implementation.md
- docs/04-tools-stack.md
- docs/05-problem-solving.md

## extract/ (5)
- extract/__init__.py
- extract/config.py
- extract/api_client.py
- extract/s3_writer.py
- extract/run_extract.py

## api/ (4)
- api/__init__.py
- api/database.py
- api/routes.py
- api/main.py

## warehouse/ (3)
- warehouse/__init__.py
- warehouse/duckdb_loader.py
- warehouse/redshift_loader.py

## orchestration/ (2)
- orchestration/__init__.py
- orchestration/run_pipeline.py

## semantic/ (2)
- semantic/__init__.py
- semantic/metrics.py

## dbt_project/ (16)
- dbt_project/dbt_project.yml
- dbt_project/macros/cents_to_dollars.sql
- dbt_project/macros/generate_schema_name.sql
- dbt_project/models/sources.yml
- dbt_project/models/staging/stg_orders.sql
- dbt_project/models/staging/stg_products.sql
- dbt_project/models/staging/stg_customers.sql
- dbt_project/models/intermediate/int_order_lines_enriched.sql
- dbt_project/models/intermediate/int_customer_orders.sql
- dbt_project/models/intermediate/int_customer_activity.sql
- dbt_project/models/marts/mart_orders.sql
- dbt_project/models/marts/mart_order_lines.sql
- dbt_project/models/marts/mart_customers.sql
- dbt_project/models/marts/mart_revenue_daily.sql
- dbt_project/models/marts/mart_customer_churn_monthly.sql
- dbt_project/tests/assert_revenue_non_negative.sql

---

**Total: 41 files**

Verify in Terminal:
```bash
find ~/Desktop/project2 -type f | wc -l
# Should print: 41
```

Open in Cursor: **File → Open Folder → Desktop → project2**
