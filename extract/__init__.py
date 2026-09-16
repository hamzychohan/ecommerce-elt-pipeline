"""Python extraction layer: pull data from mock REST API and land in S3."""

from extract.api_client import fetch_entity, fetch_page, paginate
from extract.run_extract import extract_entity, run_extract

__all__ = [
    "fetch_entity",
    "fetch_page",
    "paginate",
    "extract_entity",
    "run_extract",
]
