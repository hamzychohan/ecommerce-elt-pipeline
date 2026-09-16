"""Load raw S3 or local data into DuckDB for local development."""

import logging
import os
from glob import glob
from pathlib import Path
from typing import Any

import duckdb

from extract.config import get_local_data_dir, get_s3_bucket, get_s3_prefix, use_local_files

logger = logging.getLogger(__name__)

_ENTITIES = ["products", "users", "carts"]


def get_duckdb_path() -> str:
    """Return the local DuckDB file path."""
    return os.getenv("DUCKDB_PATH", "./warehouse/ecommerce.duckdb")


def connect(path: str | None = None):
    """Open a DuckDB connection."""
    db_path = path or get_duckdb_path()
    logger.info("Connecting to DuckDB at %s", db_path)
    return duckdb.connect(db_path)


def register_s3(conn) -> None:
    """Install and configure httpfs for S3 reads."""
    conn.execute("INSTALL httpfs;")
    conn.execute("LOAD httpfs;")

    aws_region = os.getenv("AWS_REGION", "us-east-1")
    aws_key = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY", "")

    conn.execute(f"SET s3_region='{aws_region}';")
    if aws_key:
        conn.execute(f"SET s3_access_key_id='{aws_key}';")
    if aws_secret:
        conn.execute(f"SET s3_secret_access_key='{aws_secret}';")

    logger.info("S3/httpfs configured for region=%s", aws_region)


def load_raw_entity(conn, entity: str, s3_uri: str) -> None:
    """Load raw files for one entity into a raw schema table using schema inference."""
    create_raw_schema(conn)
    table_ref = f"raw.{entity}"

    drop_sql = f"DROP TABLE IF EXISTS {table_ref};"
    conn.execute(drop_sql)

    if s3_uri.endswith(".parquet"):
        conn.execute(f"CREATE TABLE {table_ref} AS SELECT * FROM read_parquet('{s3_uri}');")
    elif s3_uri.endswith(".bson"):
        json_uri = s3_uri.replace(".bson", ".json")
        logger.info("Mock converting %s → %s", s3_uri, json_uri)
        conn.execute(f"CREATE TABLE {table_ref} AS SELECT * FROM read_json_auto('{json_uri}');")
    else:
        conn.execute(f"CREATE TABLE {table_ref} AS SELECT * FROM read_json_auto('{s3_uri}');")

    count = conn.execute(f"SELECT COUNT(*) FROM {table_ref};").fetchone()[0]
    logger.info("Loaded %d rows into %s", count, table_ref)


def create_raw_schema(conn) -> None:
    """Create raw schema and landing tables if they do not exist."""
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw;")
    logger.debug("Ensured schema 'raw' exists.")


def get_row_counts(conn) -> dict[str, int]:
    """Return row counts for raw landing tables."""
    counts: dict[str, int] = {}
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw';"
    ).fetchall()
    for (table_name,) in tables:
        row = conn.execute(f"SELECT COUNT(*) FROM raw.{table_name};").fetchone()
        counts[table_name] = row[0] if row else 0
    return counts


def _local_glob_pattern(entity: str) -> str:
    """Return a DuckDB-compatible glob for local raw JSON files."""
    base = Path(get_local_data_dir()).resolve()
    matches = glob(str(base / entity / "ingestion_date=*" / "*.json"))
    if not matches:
        raise FileNotFoundError(
            f"No local raw files found for '{entity}' under {base / entity}. "
            "Run the extract stage first."
        )
    return str(base / entity / "ingestion_date=*" / "*.json")


def _s3_glob_pattern(entity: str) -> str:
    """Return an S3 glob for raw JSON files."""
    bucket = get_s3_bucket()
    prefix = get_s3_prefix().strip("/")
    return f"s3://{bucket}/{prefix}/{entity}/ingestion_date=*/*.json"


def load_all_raw_entities(conn) -> dict[str, int]:
    """Load all configured entities into the raw schema from S3 or local files."""
    create_raw_schema(conn)
    if not use_local_files():
        register_s3(conn)

    counts: dict[str, int] = {}
    for entity in _ENTITIES:
        pattern = _local_glob_pattern(entity) if use_local_files() else _s3_glob_pattern(entity)
        load_raw_entity(conn, entity, pattern)
        row = conn.execute(f"SELECT COUNT(*) FROM raw.{entity};").fetchone()
        counts[entity] = row[0] if row else 0

    logger.info("Loaded raw entities: %s", counts)
    return counts
