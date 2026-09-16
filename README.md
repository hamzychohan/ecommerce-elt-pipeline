# E-Commerce ELT Data Warehouse

An end-to-end **Extract → Load → Transform (ELT)** pipeline that ingests e-commerce data from a mock REST API, lands it in a raw layer (local files or S3), transforms it with dbt, and serves analytics from DuckDB—with a semantic layer for revenue and churn metrics.

## Architecture

```
Mock REST API  →  Python Extractor  →  Raw Layer  →  DuckDB  →  dbt (staging → marts)  →  Reports
```

Open **http://localhost:8000** after starting the API for the project dashboard.

## Quick Start (Local)

```bash
# 1. Install dependencies
python -m venv venv && source venv/bin/activate
pip install -r requirements_app.txt
pip install -r requirements_dbt.txt   # separate venv recommended: venv_dbt

# 2. Configure environment
cp .env.example .env

# 3. Start the mock API
uvicorn api.main:app --reload --port 8000

# 4. Run the full pipeline (uses local files — no AWS required)
USE_LOCAL_FILES=true python -m orchestration.run_pipeline duckdb

# 5. Generate the analytics report
python -m reports.generate_report
```

## Quick Start (Docker)

```bash
# Fix Docker/Colima if needed (Intel Macs need: brew install qemu)
make setup-docker

# Option A: API only
make api

# Option B: Full demo — pipeline + analytics report
make demo

# Option C: Generate report from existing DuckDB warehouse
make reports
```

See [README_DOCKER.md](README_DOCKER.md) for detailed Docker instructions and troubleshooting.

## Project Structure

```
project2_complete/
├── api/                    # Mock REST API (FastAPI)
├── extract/                # API → raw layer ingestion
├── warehouse/              # DuckDB / Redshift loaders
├── orchestration/          # Full pipeline runner
├── reports/                # Analytics report generator
├── semantic/               # Revenue & churn metric helpers
├── dbt_project/            # dbt models (staging → marts)
├── scripts/setup-docker.sh # Docker/Colima recovery helper
├── docker-compose.yml      # API, pipeline, and reports services
├── Dockerfile              # Main application image
├── Dockerfile.reports      # Lightweight DuckDB reports image
└── docs/                   # Architecture and workflow docs
```

## Mart Tables

| Table | Description |
|-------|-------------|
| `mart_revenue_daily` | Daily gross revenue and order counts |
| `mart_customers` | Customer lifetime value and order frequency |
| `mart_orders` | Order-level facts |
| `mart_order_lines` | Line-item revenue by product category |
| `mart_customer_churn_monthly` | Monthly cohort churn rates |

## Documentation

| Document | Purpose |
|----------|---------|
| [Architecture Overview](docs/01-architecture-overview.md) | System design and data flow |
| [Workflow](docs/02-workflow.md) | Step-by-step pipeline stages |
| [Techniques & Implementation](docs/03-techniques-and-implementation.md) | dbt patterns and SQL techniques |
| [Tools Stack](docs/04-tools-stack.md) | Python, dbt, S3, DuckDB setup |
| [Problem Solving](docs/05-problem-solving.md) | Debugging and operations |
| [Docker Guide](README_DOCKER.md) | Container deployment and Colima fixes |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_LOCAL_FILES` | `false` | Use `./local_data` instead of S3 |
| `API_BASE_URL` | `http://localhost:8000/api/v1` | Mock API endpoint |
| `DUCKDB_PATH` | `./warehouse/ecommerce.duckdb` | DuckDB warehouse file |
| `LOCAL_DATA_DIR` | `./local_data` | Local raw file storage |
| `S3_BUCKET` | — | S3 bucket (required when `USE_LOCAL_FILES=false`) |

## Target Stack

- **Extract / orchestrate:** Python (async, concurrent)
- **Raw storage:** Local files or Amazon S3
- **Transform:** dbt (SQL + Jinja)
- **Warehouse:** DuckDB (local/dev) or Amazon Redshift (production)
- **Reports:** Python + DuckDB analytics queries
