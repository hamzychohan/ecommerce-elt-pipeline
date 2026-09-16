"""Write raw ingestion batches to local files (S3 simulation)."""

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID


def build_local_path(
    base_dir: str,
    entity: str,
    ingestion_date: date,
    batch_id: UUID | str,
    extension: str = "json",
) -> str:
    """Build a partitioned local file path for a raw batch."""
    date_str = ingestion_date.strftime("%Y-%m-%d")
    path = f"{base_dir}/{entity}/ingestion_date={date_str}/{batch_id}.{extension}"
    return path


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
    base_dir: str,
    path: str,
    records: list[dict[str, Any]],
) -> str:
    """Serialize records to JSON and write to local file. Returns the file URI."""
    full_path = Path(base_dir) / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    body = "\n".join(json.dumps(r, default=str) for r in records)
    
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(body)
    
    uri = f"file://{full_path.absolute()}"
    return uri


def list_raw_partitions(base_dir: str, entity: str, ingestion_date: date) -> list[str]:
    """List local files under a given entity/date partition."""
    date_str = ingestion_date.strftime("%Y-%m-%d")
    partition_dir = Path(base_dir) / entity / f"ingestion_date={date_str}"
    
    if not partition_dir.exists():
        return []
    
    files = []
    for file_path in partition_dir.glob("*.json"):
        rel_path = file_path.relative_to(base_dir)
        files.append(str(rel_path))
    
    return files