-- Schema Definition for E-Commerce Data Warehouse

-- 1. Raw Schema (Inferred from BSON/JSON/Parquet, mocked definition)
CREATE SCHEMA IF NOT EXISTS raw;

-- 2. Marts Schema (Final modeled tables)
CREATE SCHEMA IF NOT EXISTS marts;

-- Customers Table (Dim)
CREATE TABLE IF NOT EXISTS marts.mart_customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    customer_unique_id VARCHAR(50) NOT NULL,
    customer_zip_code_prefix VARCHAR(10),
    customer_city VARCHAR(100),
    customer_state VARCHAR(2)
);

-- Products Table (Dim)
CREATE TABLE IF NOT EXISTS marts.mart_products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_category_name VARCHAR(100),
    product_name_length SMALLINT,
    product_description_length SMALLINT,
    product_photos_qty SMALLINT,
    product_weight_g INT,
    product_length_cm SMALLINT,
    product_height_cm SMALLINT,
    product_width_cm SMALLINT
);

-- Orders Table (Fact)
CREATE TABLE IF NOT EXISTS marts.mart_orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES marts.mart_customers(customer_id),
    order_status VARCHAR(30),
    order_purchase_timestamp TIMESTAMP,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);

-- Order Lines Table (Fact)
CREATE TABLE IF NOT EXISTS marts.mart_order_lines (
    order_id VARCHAR(50) NOT NULL REFERENCES marts.mart_orders(order_id),
    order_item_id SMALLINT NOT NULL,
    product_id VARCHAR(50) NOT NULL REFERENCES marts.mart_products(product_id),
    seller_id VARCHAR(50),
    shipping_limit_date TIMESTAMP,
    price DECIMAL(10, 2),
    freight_value DECIMAL(10, 2),
    PRIMARY KEY (order_id, order_item_id)
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON marts.mart_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_product_id ON marts.mart_order_lines(product_id);
CREATE INDEX IF NOT EXISTS idx_orders_purchase_date ON marts.mart_orders(order_purchase_timestamp);
