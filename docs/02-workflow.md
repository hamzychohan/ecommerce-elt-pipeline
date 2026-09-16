# Full ELT Workflow

This document details the complete end-to-end data workflow, from the mock API all the way to the semantic layer, including recent enterprise capabilities and BSON handling.

## Phase 1: Asynchronous Extraction

1. **Trigger**: The pipeline is orchestrated via `orchestration/run_pipeline.py`.
2. **API Request**: `extract/run_extract.py` utilizes `asyncio` to make concurrent HTTP requests to the mock API endpoints (`/orders`, `/products`, `/customers`).
3. **Authentication**: The API client passes an `X-API-Key` header (`secret-token`) to bypass the FastAPI security layer.
4. **Data Retrieval**: The API returns data in various formats, potentially including JSON or BSON.

## Phase 2: Secure S3 Landing

1. **Partitioning**: The extracted payloads are partitioned by date (`ingestion_date=YYYY-MM-DD/`) in the raw S3 bucket.
2. **Format**: Data is either dumped as `.json`, `.bson`, or compressed into `.parquet` via `extract/s3_writer.py`.
3. **Encryption**: All files written to S3 use server-side encryption (KMS/AES-256) at rest.

## Phase 3: Dynamic Warehouse Loading

1. **Connection**: `warehouse/duckdb_loader.py` opens a secure connection to the DuckDB instance.
2. **BSON Conversion (Mock)**: If the file is a `.bson` file, a Python pre-processor intercepts it and converts the binary stream into standard JSON.
3. **Schema Inference**: DuckDB utilizes `read_parquet()` or `read_json_auto()` to automatically infer the schema of the files.
4. **Raw Tables**: DuckDB dynamically creates tables in the `raw` schema (e.g., `raw.orders`, `raw.products`) without any hardcoded DDL.

## Phase 4: dbt Transformation

1. **Staging**: `dbt run --select staging` cleans the raw tables (renaming, type casting).
2. **Intermediate**: `dbt run --select intermediate` joins the staging tables into business logic CTEs.
3. **Marts (Incremental)**: `dbt run --select marts` builds the final tables defined in `schema.sql`. Large tables utilize incremental materialization to only process new records.

## Phase 5: Semantic Layer & Metrics

1. **Definitions**: `semantic/metrics.py` defines business logic (e.g., Daily Revenue, Customer Churn).
2. **Execution**: The semantic layer queries the transformed `marts` tables to present a unified, single source of truth for downstream BI tools and dashboards.
