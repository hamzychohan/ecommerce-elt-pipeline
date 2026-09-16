"""PostgreSQL connection helpers for the mock API."""

import os
from contextlib import contextmanager
from typing import Any

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def get_connection_string() -> str:
    """Return the PostgreSQL connection string from environment."""
    url = os.getenv("POSTGRES_URL")
    if not url:
        raise ValueError("POSTGRES_URL environment variable is not set.")
    return url


@contextmanager
def get_connection():
    """Return a database connection (context-managed in implementation)."""
    conn = psycopg2.connect(get_connection_string())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Run a read query and return rows as dicts."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params or {})
            return [dict(row) for row in cur.fetchall()]


def fetch_one(query: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Run a read query and return a single row or None."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params or {})
            row = cur.fetchone()
            return dict(row) if row else None
