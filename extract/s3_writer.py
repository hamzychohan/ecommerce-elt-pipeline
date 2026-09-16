"""Write raw ingestion batches to S3."""

import io
import json
import os
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

import boto3

_s3_client = None


def _get_s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-1"))
    return _s3_client


def build_s3_key(
    prefix: str,
    entity: str,
    ingestion_date: date,
    batch_id: UUID | str,
    extension: str = "json",
) -> str:
    """Build a partitioned S3 object key for a raw batch."""
    date_str = ingestion_date.strftime("%Y-%m-%d")
    return f"{prefix}/{entity}/ingestion_date={date_str}/{batch_id}.{extension}"


def enrich_records(
    records: list[dict[str, Any]],
    source: str,
    batch_id: UUID | str,
    ingested_at: datetime | None = None,
) -> list[dict[str, Any]]:
    """Attach ingestion metadata fields to each raw record."""
    ts = (ingested_at or datetime.now(tz=timezone.utc)).isoformat()
    return [
        {
            **record,
            "_source": source,
            "_batch_id": str(batch_id),
            "_ingested_at": ts,
        }
        for record in records
    ]


def write_json_batch(
    bucket: str,
    key: str,
    records: list[dict[str, Any]],
) -> str:
    """Serialize records to JSON and upload to S3. Returns the S3 URI."""
    body = "\n".join(json.dumps(r, default=str) for r in records)
    _get_s3().put_object(
        Bucket=bucket,
        Key=key,
        Body=body.encode("utf-8"),
        ContentType="application/json",
    )
    uri = f"s3://{bucket}/{key}"
    return uri


def write_parquet_batch(
    bucket: str,
    key: str,
    records: list[dict[str, Any]],
) -> str:
    """Serialize records to Parquet and upload to S3. Returns the S3 URI."""
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ImportError("pyarrow is required for Parquet output: pip install pyarrow") from exc

    table = pa.Table.from_pylist(records)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    buf.seek(0)
    _get_s3().put_object(
        Bucket=bucket,
        Key=key,
        Body=buf.read(),
        ContentType="application/octet-stream",
    )
    uri = f"s3://{bucket}/{key}"
    return uri


def list_raw_partitions(bucket: str, entity: str, ingestion_date: date) -> list[str]:
    """List S3 keys under a given entity/date partition."""
    date_str = ingestion_date.strftime("%Y-%m-%d")
    prefix = f"raw/{entity}/ingestion_date={date_str}/"
    paginator = _get_s3().get_paginator("list_objects_v2")
    keys: list[str] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys
