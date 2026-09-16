# Docker Deployment

Run the full ELT pipeline and analytics reports inside Docker containers.

## Prerequisites

- Docker Compose v2+
- **Colima** (macOS without Docker Desktop) or Docker Desktop

### Fix: "Cannot connect to the Docker daemon"

If you see:

```
Cannot connect to the Docker daemon
/var/run/docker.sock: no such file
```

Run the setup helper:

```bash
chmod +x scripts/setup-docker.sh
./scripts/setup-docker.sh
# or
make setup-docker
```

**Intel Mac (macOS < 15.5):** Colima's default VZ VM may hang. Install QEMU first:

```bash
brew install qemu colima docker
colima delete          # reset if a previous start failed
./scripts/setup-docker.sh
```

## Services

| Service | Profile | Description |
|---------|---------|-------------|
| `api` | default | Mock REST API on port 8000 |
| `pipeline` | `pipeline` | Extract → DuckDB load → dbt transform |
| `reports` | `reports` | Analytics report from DuckDB warehouse |
| `full-stack` | `demo` | Pipeline + report in one run |

## Commands

```bash
# Build all images
docker compose build

# Start API only (dashboard at http://localhost:8000)
docker compose up api

# Run pipeline (local files mode — no AWS credentials needed)
docker compose --profile pipeline up pipeline

# Generate analytics report from warehouse/ecommerce.duckdb
docker compose --profile reports run --rm reports

# Full demo: wait for API → run pipeline → print report
docker compose --profile demo up full-stack

# Makefile shortcuts
make api
make pipeline
make reports
make demo
```

## Reports Container

The `Dockerfile.reports` image is a lightweight container that mounts the DuckDB warehouse read-only and prints the analytics report:

```bash
docker build -f Dockerfile.reports -t project2-reports .
docker run --rm \
  -v "$PWD/warehouse:/app/warehouse:ro" \
  -e DUCKDB_PATH=/app/warehouse/ecommerce.duckdb \
  project2-reports
```

Example output:

```
=== ELT PIPELINE SUCCESS DEMO ===

PIPELINE RESULTS:
   EXTRACTED: 2,700 total records from mock API
   TRANSFORMED: 5 mart tables created by dbt

SAMPLE ANALYTICS:
   Daily Revenue (first 5 days):
      2025-01-04: 2 orders, $690.29
   Top Customers by Revenue:
      cust-00348: 11 orders, $5,870.81
   Top Product Categories:
      books: 416 lines, $216,135.54
```

## AWS / S3 Mode

To use S3 instead of local files, set environment variables and mount AWS credentials:

```bash
docker compose run --rm \
  -e USE_LOCAL_FILES=false \
  -e AWS_ACCESS_KEY_ID=... \
  -e AWS_SECRET_ACCESS_KEY=... \
  -e S3_BUCKET=elt-bucket-s3 \
  -v "$HOME/.aws:/home/appuser/.aws:ro" \
  pipeline
```

## Verify S3 Upload (AWS mode)

```bash
aws s3 ls s3://elt-bucket-s3/raw/orders/ --region eu-north-1
aws s3 ls s3://elt-bucket-s3/raw/products/ --region eu-north-1
aws s3 ls s3://elt-bucket-s3/raw/customers/ --region eu-north-1
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Docker daemon not running | `make setup-docker` |
| Colima stuck on SSH (Intel Mac) | `brew install qemu && colima delete && colima start --vm-type qemu` |
| Warehouse not found for reports | Run pipeline first: `make pipeline` or `make demo` |
| dbt profile path error | Set `DUCKDB_PATH=/app/warehouse/ecommerce.duckdb` in container |
| API not ready | Pipeline waits for `/health`; start API first or use `make demo` |
