"""Orchestrate extraction from API to S3 raw layer."""

import asyncio
import logging
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from typing import Any

from extract.api_client import fetch_entity
from extract.config import get_api_base_url, get_entities, get_s3_bucket, get_s3_prefix, use_local_files, get_local_data_dir
from extract.validators import validate_records

# Import writers based on configuration
if use_local_files():
    from extract.local_writer import build_local_path as build_s3_key, enrich_records, write_json_batch
else:
    from extract.s3_writer import build_s3_key, enrich_records, write_json_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


def _sync_extract_entity(entity: str, ingestion_date: date) -> dict[str, Any]:
    """Blocking extraction for one entity — runs inside a thread pool."""
    base_url = get_api_base_url()
    
    if use_local_files():
        data_dir = get_local_data_dir()
    else:
        bucket = get_s3_bucket()
        
    prefix = get_s3_prefix()
    batch_id = uuid.uuid4()

    logger.info("Extracting entity='%s' from %s", entity, base_url)
    records = fetch_entity(base_url, entity)
    
    valid_records = validate_records(entity, records)

    enriched = enrich_records(
        valid_records,
        source=entity,
        batch_id=batch_id,
        ingested_at=datetime.now(tz=timezone.utc),
    )

    if use_local_files():
        key = build_s3_key(prefix, entity, ingestion_date, batch_id, extension="json")
        uri = write_json_batch(data_dir, key, enriched)
    else:
        key = build_s3_key(prefix, entity, ingestion_date, batch_id, extension="json")
        uri = write_json_batch(bucket, key, enriched)

    logger.info("Wrote %d records for '%s' → %s", len(enriched), entity, uri)
    return {
        "entity": entity,
        "status": "success",
        "rows": len(enriched),
        "s3_uri": uri,
        "batch_id": str(batch_id),
    }


async def extract_entity(entity: str, ingestion_date: date | None = None) -> dict[str, Any]:
    """Extract one entity and write partitioned raw files to S3 asynchronously."""
    today = ingestion_date or date.today()
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(_executor, _sync_extract_entity, entity, today)
        return result
    except Exception as exc:
        logger.error("Failed to extract entity='%s': %s", entity, exc)
        return {"entity": entity, "status": "failed", "error": str(exc), "rows": 0}


async def run_extract(entities: list[str] | None = None) -> dict[str, Any]:
    """Extract all configured entities concurrently. Returns summary stats per entity."""
    if entities is None:
        entities = get_entities()

    logger.info("Starting concurrent extraction for entities: %s", entities)
    tasks = [extract_entity(entity) for entity in entities]
    results = await asyncio.gather(*tasks)

    summary = {result["entity"]: result for result in results}
    log_extract_summary(summary)
    return summary


def log_extract_summary(summary: dict[str, Any]) -> None:
    """Log record counts, batch IDs, and any failures from an extract run."""
    total_rows = 0
    failures = []
    for entity, info in summary.items():
        rows = info.get("rows", 0)
        status = info.get("status", "unknown")
        batch_id = info.get("batch_id", "n/a")
        total_rows += rows
        if status != "success":
            failures.append(entity)
        logger.info(
            "[%s] status=%s rows=%d batch_id=%s",
            entity,
            status,
            rows,
            batch_id,
        )
    logger.info("Extract complete. Total rows: %d. Failures: %s", total_rows, failures or "none")


def main() -> None:
    """CLI entry point for the extract job."""
    entities = sys.argv[1:] if len(sys.argv) > 1 else None
    summary = asyncio.run(run_extract(entities))
    has_failures = any(v.get("status") != "success" for v in summary.values())
    sys.exit(1 if has_failures else 0)


if __name__ == "__main__":
    main()
