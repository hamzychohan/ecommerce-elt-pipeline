"""Business metric definitions and query helpers."""

import logging
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


def get_revenue_definition() -> dict[str, Any]:
    """Return the canonical gross_revenue metric definition."""
    return {
        "name": "gross_revenue",
        "label": "Gross Revenue",
        "description": (
            "Total price paid by customers (excluding freight) for orders with "
            "status in ['delivered', 'shipped', 'invoiced', 'approved']."
        ),
        "source_model": "mart_revenue_daily",
        "grain": "day",
        "measure": "SUM(gross_revenue_dollars)",
        "dimensions": ["order_date", "product_category_name"],
        "filters": {"order_status": ["delivered", "shipped", "invoiced", "approved"]},
        "unit": "USD",
    }


def get_churn_definition() -> dict[str, Any]:
    """Return the canonical customer_churn_rate metric definition."""
    return {
        "name": "customer_churn_rate",
        "label": "Monthly Customer Churn Rate",
        "description": (
            "Percentage of customers who were active in the prior month but placed "
            "no order in the current month. A customer is 'active' if they placed "
            "at least one order within the last 90 days."
        ),
        "source_model": "mart_customer_churn_monthly",
        "grain": "month",
        "measure": "AVG(churn_rate)",
        "dimensions": ["cohort_month"],
        "unit": "ratio (0–1)",
    }


def compute_gross_revenue(
    conn,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """Query daily gross revenue from mart_revenue_daily."""
    conditions = []
    params: list[Any] = []

    if start_date:
        conditions.append("order_date >= ?")
        params.append(start_date.isoformat())
    if end_date:
        conditions.append("order_date <= ?")
        params.append(end_date.isoformat())

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT
            order_date,
            total_orders,
            gross_revenue_dollars,
            avg_order_value_dollars
        FROM mart_revenue_daily
        {where_clause}
        ORDER BY order_date
    """
    try:
        result = conn.execute(sql, params).fetchdf()
        return result.to_dict(orient="records")
    except Exception as exc:
        logger.error("compute_gross_revenue failed: %s", exc)
        return []


def compute_churn_rate(
    conn,
    month: date | None = None,
) -> dict[str, Any]:
    """Query monthly churn rate from mart_customer_churn_monthly."""
    if month:
        sql = """
            SELECT
                cohort_month,
                active_customers_prior,
                churned_customers,
                churn_rate
            FROM mart_customer_churn_monthly
            WHERE cohort_month = ?
            ORDER BY cohort_month DESC
            LIMIT 1
        """
        params = [month.strftime("%Y-%m-01")]
    else:
        sql = """
            SELECT
                cohort_month,
                active_customers_prior,
                churned_customers,
                churn_rate
            FROM mart_customer_churn_monthly
            ORDER BY cohort_month DESC
            LIMIT 1
        """
        params = []

    try:
        rows = conn.execute(sql, params).fetchdf().to_dict(orient="records")
        return rows[0] if rows else {}
    except Exception as exc:
        logger.error("compute_churn_rate failed: %s", exc)
        return {}


def validate_revenue_non_negative(records: list[dict[str, Any]]) -> bool:
    """Return True if all revenue values are >= 0."""
    for record in records:
        revenue = record.get("gross_revenue_dollars", 0)
        if revenue is not None and float(revenue) < 0:
            logger.warning("Negative revenue detected: %s", record)
            return False
    return True


def validate_churn_rate_bounds(rate: float) -> bool:
    """Return True if churn rate is between 0 and 1 inclusive."""
    valid = 0.0 <= rate <= 1.0
    if not valid:
        logger.warning("Churn rate out of bounds: %s", rate)
    return valid
