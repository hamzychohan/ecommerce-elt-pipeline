"""End-to-end pipeline orchestration."""

import asyncio
import logging
import os
import shutil
import subprocess
import sys
from typing import Any, Literal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def run_extract_stage() -> dict[str, Any]:
    """Run Python extract → S3."""
    logger.info("=== Stage 1: Extract (API → S3) ===")
    from extract.run_extract import run_extract

    summary = await run_extract()
    total_rows = sum(v.get("rows", 0) for v in summary.values())
    failures = [k for k, v in summary.items() if v.get("status") != "success"]
    if failures:
        logger.error("Extract failures: %s", failures)
    logger.info("Extract complete. total_rows=%d failures=%s", total_rows, failures or "none")
    return {"status": "failed" if failures else "success", "rows": total_rows, "detail": summary}


async def run_load_stage(warehouse: str = "duckdb") -> dict[str, Any]:
    """Load S3 data into Warehouse with Schema Inference."""
    logger.info("=== Stage 2: Load (S3 → %s) ===", warehouse.upper())

    if warehouse == "duckdb":
        from warehouse.duckdb_loader import connect, load_all_raw_entities

        conn = connect()
        try:
            counts = load_all_raw_entities(conn)
        finally:
            conn.close()
        tables_loaded = len(counts)
        logger.info("DuckDB load complete. tables=%d counts=%s", tables_loaded, counts)
        return {"status": "success", "tables_loaded": tables_loaded, "row_counts": counts}

    elif warehouse == "redshift":
        logger.info("Redshift load requires COPY commands — skipping in dry-run mode.")
        return {"status": "skipped", "reason": "Redshift credentials not configured for this run."}

    else:
        raise ValueError(f"Unknown warehouse: {warehouse!r}")


def locate_dbt_executable() -> str:
    """Find the dbt executable to run in Docker and local environments."""
    local_dbt = os.path.join(os.getcwd(), "venv_dbt", "bin", "dbt")
    if os.path.isfile(local_dbt) and os.access(local_dbt, os.X_OK):
        return local_dbt

    system_dbt = shutil.which("dbt")
    if system_dbt:
        return system_dbt

    raise FileNotFoundError(
        "dbt executable not found. Install dbt in ./venv_dbt or make sure it is on PATH."
    )


async def run_dbt_stage(select: str | None = None, target: str | None = None) -> dict[str, Any]:
    """Run dbt build (models + tests)."""
    logger.info("=== Stage 3: Transform (dbt build) ===")
    dbt_binary = locate_dbt_executable()
    cmd = [dbt_binary, "build", "--project-dir", "dbt_project", "--profiles-dir", "dbt_project/profiles"]
    if select:
        cmd += ["--select", select]
    if target:
        cmd += ["--target", target]

    logger.info("Running: %s", " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        logger.error("dbt failed (rc=%d):\n%s", proc.returncode, stderr.decode())
        return {"status": "failed", "returncode": proc.returncode, "stderr": stderr.decode()}

    logger.info("dbt build succeeded:\n%s", stdout.decode())
    return {"status": "success", "returncode": 0}


async def run_full_pipeline(warehouse: Literal["duckdb", "redshift"] = "duckdb") -> dict[str, Any]:
    """Run extract → load → dbt transform → test."""
    logger.info("======= Starting Full ELT Pipeline (%s) =======", warehouse.upper())

    extract_result = await run_extract_stage()
    load_result = await run_load_stage(warehouse=warehouse)
    transform_result = await run_dbt_stage(select="marts", target=warehouse)

    overall = (
        "success"
        if all(
            r.get("status") in ("success", "skipped")
            for r in [extract_result, load_result, transform_result]
        )
        else "partial_failure"
    )

    pipeline_result = {
        "overall_status": overall,
        "warehouse": warehouse,
        "extract": extract_result,
        "load": load_result,
        "transform": transform_result,
    }

    logger.info("======= Pipeline Finished: %s =======", overall.upper())
    return pipeline_result


def main() -> None:
    """CLI entry point for the full ELT pipeline."""
    warehouse: Literal["duckdb", "redshift"] = "duckdb"
    if len(sys.argv) > 1 and sys.argv[1] in ("duckdb", "redshift"):
        warehouse = sys.argv[1]  # type: ignore[assignment]

    result = asyncio.run(run_full_pipeline(warehouse=warehouse))
    sys.exit(0 if result.get("overall_status") == "success" else 1)


if __name__ == "__main__":
    main()
