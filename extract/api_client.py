"""HTTP client for the mock e-commerce REST API."""

import logging
import time
from collections.abc import Iterator
from typing import Any

import requests

from extract.config import get_api_base_url

logger = logging.getLogger(__name__)

_DEFAULT_API_KEY = "secret-token"


def _get_session(session: requests.Session | None = None) -> requests.Session:
    if session is not None:
        return session
    s = requests.Session()
    s.headers.update({"X-API-Key": _DEFAULT_API_KEY})
    return s


def build_url(base_url: str, entity: str, skip: int, limit: int) -> str:
    """Build a paginated list endpoint URL for the given entity."""
    base_url = base_url.rstrip("/")
    return f"{base_url}/{entity}?skip={skip}&limit={limit}"


def fetch_page(url: str, session: requests.Session | None = None) -> dict[str, Any]:
    """Fetch a single API page and return parsed JSON."""
    s = _get_session(session)
    
    def _do_fetch():
        response = s.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
        
    return retry_request(_do_fetch, max_retries=5, backoff_seconds=2.0)


def paginate(
    base_url: str,
    entity: str,
    limit: int = 100,
    session: requests.Session | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield each page payload until no more pages remain."""
    s = _get_session(session)
    skip = 0
    while True:
        url = build_url(base_url, entity, skip, limit)
        logger.debug("Fetching %s", url)
        payload = fetch_page(url, session=s)
        yield payload
        total = payload.get("total", 0)
        skip += limit
        if skip >= total:
            break


def fetch_entity(
    base_url: str,
    entity: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Fetch all records for an entity across paginated responses."""
    all_records: list[dict[str, Any]] = []
    with requests.Session() as session:
        session.headers.update({"X-API-Key": _DEFAULT_API_KEY})
        for page_payload in paginate(base_url, entity, limit=limit, session=session):
            records = page_payload.get(entity, [])
            all_records.extend(records)
            logger.info(
                "Fetched %d records for '%s' (cumulative: %d)",
                len(records),
                entity,
                len(all_records),
            )
    return all_records


def retry_request(
    func,
    max_retries: int = 5,
    backoff_seconds: float = 2.0,
):
    """Wrap an HTTP call with exponential backoff and rate limit handling."""
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except requests.RequestException as exc:
            last_exc = exc
            
            # For HTTP errors, check the status code
            if isinstance(exc, requests.HTTPError) and exc.response is not None:
                status = exc.response.status_code
                # Do not retry client errors (4xx) except 429 Too Many Requests
                if 400 <= status < 500 and status != 429:
                    logger.error("Non-retriable client error %d: %s", status, exc)
                    raise
            
            if attempt == max_retries:
                break
                
            wait = backoff_seconds * (2 ** (attempt - 1))
            
            # Respect Retry-After header for 429 Too Many Requests
            if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code == 429:
                retry_after = exc.response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait = float(retry_after)
            
            logger.warning(
                "Request failed (attempt %d/%d): %s. Retrying in %.1fs…",
                attempt,
                max_retries,
                exc,
                wait,
            )
            time.sleep(wait)
            
    raise RuntimeError(f"All {max_retries} retries exhausted.") from last_exc
