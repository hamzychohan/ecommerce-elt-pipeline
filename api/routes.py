"""REST route handlers for orders, products, and customers."""

import random
from datetime import datetime, timedelta
from typing import Any

_RNG = random.Random(42)

CITIES = ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Salvador", "Curitiba", "Fortaleza"]
STATES = ["SP", "RJ", "MG", "BA", "PR", "CE"]
CATEGORIES = ["electronics", "clothing", "home_appliances", "books", "sports", "beauty", "toys"]
ORDER_STATUSES = ["delivered", "shipped", "processing", "cancelled", "invoiced", "approved"]

_BASE_DATE = datetime(2025, 1, 1)


def _make_customer(idx: int) -> dict[str, Any]:
    rng = random.Random(idx)
    city_i = rng.randint(0, len(CITIES) - 1)
    return {
        "customer_id": f"cust-{idx:05d}",
        "customer_unique_id": f"uniq-{idx:05d}",
        "customer_zip_code_prefix": str(rng.randint(10000, 99999)),
        "customer_city": CITIES[city_i],
        "customer_state": STATES[city_i],
    }


def _make_product(idx: int) -> dict[str, Any]:
    rng = random.Random(1000 + idx)
    return {
        "product_id": f"prod-{idx:05d}",
        "product_category_name": rng.choice(CATEGORIES),
        "product_name_length": rng.randint(10, 60),
        "product_description_length": rng.randint(100, 1000),
        "product_photos_qty": rng.randint(1, 6),
        "product_weight_g": rng.randint(100, 30000),
        "product_length_cm": rng.randint(10, 80),
        "product_height_cm": rng.randint(5, 50),
        "product_width_cm": rng.randint(10, 60),
    }


def _make_order(idx: int) -> dict[str, Any]:
    rng = random.Random(2000 + idx)
    purchase_ts = _BASE_DATE + timedelta(days=rng.randint(0, 540), hours=rng.randint(0, 23))
    approved = purchase_ts + timedelta(hours=rng.randint(1, 12))
    delivered_carrier = approved + timedelta(days=rng.randint(1, 5))
    delivered_customer = delivered_carrier + timedelta(days=rng.randint(1, 10))
    estimated_delivery = purchase_ts + timedelta(days=rng.randint(10, 30))
    status = rng.choice(ORDER_STATUSES)
    price_cents = rng.randint(500, 100000)
    return {
        "order_id": f"ord-{idx:06d}",
        "customer_id": f"cust-{rng.randint(1, 500):05d}",
        "order_status": status,
        "order_purchase_timestamp": purchase_ts.isoformat(),
        "order_approved_at": approved.isoformat(),
        "order_delivered_carrier_date": delivered_carrier.isoformat(),
        "order_delivered_customer_date": delivered_customer.isoformat() if status == "delivered" else None,
        "order_estimated_delivery_date": estimated_delivery.isoformat(),
        "price_cents": price_cents,
        "freight_value_cents": rng.randint(100, 3000),
        "product_id": f"prod-{rng.randint(1, 200):05d}",
        "order_item_id": 1,
        "seller_id": f"sell-{rng.randint(1, 50):04d}",
    }


_TOTAL_CUSTOMERS = 500
_TOTAL_PRODUCTS = 200
_TOTAL_ORDERS = 2000


def paginated_response(
    data: list[dict[str, Any]],
    page: int,
    limit: int,
    total: int,
) -> dict[str, Any]:
    """Build a standard paginated JSON response envelope."""
    return {
        "data": data,
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": max(1, (total + limit - 1) // limit),
        "has_next": (page * limit) < total,
    }


def get_orders(page: int, limit: int) -> dict[str, Any]:
    """Return paginated order records."""
    offset = (page - 1) * limit
    records = [_make_order(i) for i in range(offset + 1, min(offset + limit + 1, _TOTAL_ORDERS + 1))]
    return paginated_response(records, page, limit, _TOTAL_ORDERS)


def get_order(order_id: str) -> dict[str, Any] | None:
    """Return a single order by ID."""
    try:
        idx = int(order_id.split("-")[-1])
    except (ValueError, IndexError):
        return None
    if idx < 1 or idx > _TOTAL_ORDERS:
        return None
    return _make_order(idx)


def get_products(page: int, limit: int) -> dict[str, Any]:
    """Return paginated product catalog records."""
    offset = (page - 1) * limit
    records = [_make_product(i) for i in range(offset + 1, min(offset + limit + 1, _TOTAL_PRODUCTS + 1))]
    return paginated_response(records, page, limit, _TOTAL_PRODUCTS)


def get_product(product_id: str) -> dict[str, Any] | None:
    """Return a single product by ID."""
    try:
        idx = int(product_id.split("-")[-1])
    except (ValueError, IndexError):
        return None
    if idx < 1 or idx > _TOTAL_PRODUCTS:
        return None
    return _make_product(idx)


def get_customers(page: int, limit: int) -> dict[str, Any]:
    """Return paginated customer records."""
    offset = (page - 1) * limit
    records = [_make_customer(i) for i in range(offset + 1, min(offset + limit + 1, _TOTAL_CUSTOMERS + 1))]
    return paginated_response(records, page, limit, _TOTAL_CUSTOMERS)


def get_customer(customer_id: str) -> dict[str, Any] | None:
    """Return a single customer by ID."""
    try:
        idx = int(customer_id.split("-")[-1])
    except (ValueError, IndexError):
        return None
    if idx < 1 or idx > _TOTAL_CUSTOMERS:
        return None
    return _make_customer(idx)
