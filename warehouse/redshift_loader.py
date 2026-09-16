"""Load raw S3 data into Amazon Redshift."""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_ENTITIES = ["orders", "products", "customers"]

_DDL_TEMPLATES = {
    "orders": """
        CREATE TABLE IF NOT EXISTS raw.orders (
            order_id        VARCHAR(50),
            customer_id     VARCHAR(50),
            order_status    VARCHAR(30),
            order_purchase_timestamp TIMESTAMP,
            order_approved_at        TIMESTAMP,
            order_delivered_carrier_date  TIMESTAMP,
            order_delivered_customer_date TIMESTAMP,
            order_estimated_delivery_date TIMESTAMP,
            price_cents     BIGINT,
            freight_value_cents BIGINT,
            product_id      VARCHAR(50),
            order_item_id   SMALLINT,
            seller_id       VARCHAR(50),
            _source         VARCHAR(50),
            _batch_id       VARCHAR(50),
            _ingested_at    TIMESTAMP
        )
        DISTKEY(order_id)
        SORTKEY(order_purchase_timestamp);
    """,
    "products": """
        CREATE TABLE IF NOT EXISTS raw.products (
            product_id                  VARCHAR(50),
            product_category_name       VARCHAR(100),
            product_name_length         SMALLINT,
            product_description_length  SMALLINT,
            product_photos_qty          SMALLINT,
            product_weight_g            INT,
            product_length_cm           SMALLINT,
            product_height_cm           SMALLINT,
            product_width_cm            SMALLINT,
            _source                     VARCHAR(50),
            _batch_id                   VARCHAR(50),
            _ingested_at                TIMESTAMP
        )
        DISTKEY(product_id);
    """,
    "customers": """
        CREATE TABLE IF NOT EXISTS raw.customers (
            customer_id             VARCHAR(50),
            customer_unique_id      VARCHAR(50),
            customer_zip_code_prefix VARCHAR(10),
            customer_city           VARCHAR(100),
            customer_state          VARCHAR(2),
            _source                 VARCHAR(50),
            _batch_id               VARCHAR(50),
            _ingested_at            TIMESTAMP
        )
        DISTKEY(customer_id);
    """,
}


def get_redshift_connection():
    """Return a Redshift connection using environment credentials."""
    try:
        import psycopg2
    except ImportError as exc:
        raise ImportError("psycopg2-binary is required for Redshift: pip install psycopg2-binary") from exc

    host = os.environ["REDSHIFT_HOST"]
    port = int(os.getenv("REDSHIFT_PORT", "5439"))
    dbname = os.environ["REDSHIFT_DB"]
    user = os.environ["REDSHIFT_USER"]
    password = os.environ["REDSHIFT_PASSWORD"]

    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        connect_timeout=10,
    )
    logger.info("Connected to Redshift at %s:%d/%s", host, port, dbname)
    return conn


def copy_from_s3(
    conn,
    table: str,
    s3_uri: str,
    iam_role: str,
    file_format: str = "json",
) -> None:
    """Run COPY from S3 into a Redshift landing table."""
    format_clause = (
        "JSON 'auto'"
        if file_format.lower() == "json"
        else f"PARQUET"
    )
    sql = f"""
        COPY {table}
        FROM '{s3_uri}'
        IAM_ROLE '{iam_role}'
        {format_clause}
        TIMEFORMAT 'auto'
        TRUNCATECOLUMNS
        COMPUPDATE OFF
        STATUPDATE OFF;
    """
    with conn.cursor() as cur:
        logger.info("Running COPY: %s → %s", s3_uri, table)
        cur.execute(sql)
    conn.commit()


def create_raw_schema(conn) -> None:
    """Create raw schema and landing tables if they do not exist."""
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS raw;")
        for entity, ddl in _DDL_TEMPLATES.items():
            logger.debug("Ensuring table raw.%s exists", entity)
            cur.execute(ddl)
    conn.commit()
    logger.info("Raw schema and tables verified in Redshift.")


def get_load_errors(conn, query_id: int | None = None) -> list[dict[str, Any]]:
    """Query stl_load_errors for recent COPY failures."""
    base_sql = """
        SELECT
            query,
            filename,
            line_number,
            colname,
            type,
            col_length,
            position,
            raw_field_value,
            err_reason,
            starttime
        FROM stl_load_errors
    """
    if query_id is not None:
        sql = base_sql + " WHERE query = %s ORDER BY starttime DESC LIMIT 100;"
        params = (query_id,)
    else:
        sql = base_sql + " ORDER BY starttime DESC LIMIT 100;"
        params = ()

    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
