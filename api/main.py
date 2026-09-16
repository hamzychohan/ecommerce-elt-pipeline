"""FastAPI application entry point for the mock e-commerce API."""

import os

from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles

from api.routes import (
    get_customer,
    get_customers,
    get_order,
    get_orders,
    get_product,
    get_products,
)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == "secret-token":
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate credentials")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="E-Commerce Mock API",
        description="Mock REST API serving e-commerce orders, products, and customers for ELT pipeline ingestion.",
        version="1.0.0",
    )
    register_routes(app)

    docs_dir = os.path.join(_BASE_DIR, "docs")
    if os.path.isdir(docs_dir):
        app.mount("/docs-files", StaticFiles(directory=docs_dir), name="docs")

    return app


def register_routes(app: FastAPI) -> None:
    """Register /orders, /products, and /customers routes."""

    @app.get("/", include_in_schema=False)
    def dashboard():
        """Serve the project dashboard."""
        index_path = os.path.join(_BASE_DIR, "index.html")
        return FileResponse(index_path, media_type="text/html")

    @app.get("/health", tags=["system"], include_in_schema=False)
    def health():
        return {"status": "ok"}

    @app.get("/api/v1/orders", tags=["orders"], dependencies=[Depends(get_api_key)])
    def list_orders(page: int = Query(1, ge=1), limit: int = Query(100, ge=1, le=500)):
        return get_orders(page=page, limit=limit)

    @app.get("/api/v1/orders/{order_id}", tags=["orders"], dependencies=[Depends(get_api_key)])
    def retrieve_order(order_id: str):
        record = get_order(order_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Order '{order_id}' not found.")
        return record

    @app.get("/api/v1/products", tags=["products"], dependencies=[Depends(get_api_key)])
    def list_products(page: int = Query(1, ge=1), limit: int = Query(100, ge=1, le=500)):
        return get_products(page=page, limit=limit)

    @app.get("/api/v1/products/{product_id}", tags=["products"], dependencies=[Depends(get_api_key)])
    def retrieve_product(product_id: str):
        record = get_product(product_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found.")
        return record

    @app.get("/api/v1/customers", tags=["customers"], dependencies=[Depends(get_api_key)])
    def list_customers(page: int = Query(1, ge=1), limit: int = Query(100, ge=1, le=500)):
        return get_customers(page=page, limit=limit)

    @app.get("/api/v1/customers/{customer_id}", tags=["customers"], dependencies=[Depends(get_api_key)])
    def retrieve_customer(customer_id: str):
        record = get_customer(customer_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Customer '{customer_id}' not found.")
        return record


app = create_app()
