"""Configuration helpers for the extract pipeline."""

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def load_config() -> dict[str, Any]:
    """Load API, S3, and runtime settings from environment variables."""
    return {
        "api_base_url": get_api_base_url(),
        "api_key": os.getenv("API_KEY", "secret-token"),
        "s3_bucket": get_s3_bucket(),
        "s3_prefix": get_s3_prefix(),
        "entities": get_entities(),
        "aws_region": os.getenv("AWS_REGION", "us-east-1"),
        "duckdb_path": os.getenv("DUCKDB_PATH", "./warehouse/ecommerce.duckdb"),
        "use_local_files": use_local_files(),
        "local_data_dir": get_local_data_dir(),
    }


def get_api_base_url() -> str:
    """Return the mock REST API base URL."""
    return os.getenv("API_BASE_URL", "https://dummyjson.com")


def get_s3_bucket() -> str:
    """Return the target S3 bucket name for raw data."""
    if use_local_files():
        return "local-bucket"  # Dummy value for local development
    bucket = os.getenv("S3_BUCKET")
    if not bucket:
        raise ValueError("S3_BUCKET environment variable is not set.")
    return bucket


def get_s3_prefix() -> str:
    """Return the S3 key prefix (e.g. 'raw')."""
    return os.getenv("S3_PREFIX", "raw")


def get_entities() -> list[str]:
    """Return entity names to extract (products, users, carts)."""
    raw = os.getenv("ENTITIES", "products,users,carts")
    return [e.strip() for e in raw.split(",") if e.strip()]


def use_local_files() -> bool:
    """Check if we should use local files instead of S3."""
    return os.getenv("USE_LOCAL_FILES", "false").lower() in ("true", "1", "yes")


def get_local_data_dir() -> str:
    """Return the local directory for storing raw data files."""
    return os.getenv("LOCAL_DATA_DIR", "./local_data")
