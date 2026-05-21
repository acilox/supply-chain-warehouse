-- ============================================================
-- Supply Chain DW Snowflake Star Schema DDL
-- ============================================================

CREATE DATABASE IF NOT EXISTS SUPPLY_CHAIN_DW;
USE DATABASE SUPPLY_CHAIN_DW;
CREATE SCHEMA IF NOT EXISTS PUBLIC;

-- ============================================================
-- DIMENSIONS (SCD Type 2 for slowly-changing)
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_supplier (
    supplier_sk         NUMBER AUTOINCREMENT PRIMARY KEY,
    supplier_id         VARCHAR(64) NOT NULL,
    name                VARCHAR(256),
    country             CHAR(2),
    city                VARCHAR(128),
    quality_tier        VARCHAR(16),
    contract_terms_days NUMBER,
    effective_from      TIMESTAMP_NTZ NOT NULL,
    effective_to        TIMESTAMP_NTZ,
    is_current          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS dim_warehouse (
    warehouse_sk     NUMBER AUTOINCREMENT PRIMARY KEY,
    warehouse_id     VARCHAR(64) NOT NULL,
    name             VARCHAR(256),
    country          CHAR(2),
    city             VARCHAR(128),
    postal_code      VARCHAR(20),
    lat              DECIMAL(9, 6),
    lon              DECIMAL(9, 6),
    capacity_units   NUMBER,
    effective_from   TIMESTAMP_NTZ NOT NULL,
    effective_to     TIMESTAMP_NTZ,
    is_current       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_sk       NUMBER AUTOINCREMENT PRIMARY KEY,
    product_id       VARCHAR(64) NOT NULL,
    sku              VARCHAR(64),
    name             VARCHAR(256),
    category         VARCHAR(128),
    brand            VARCHAR(128),
    unit_of_measure  VARCHAR(16),
    is_cold_chain    BOOLEAN DEFAULT FALSE,
    effective_from   TIMESTAMP_NTZ NOT NULL,
    effective_to     TIMESTAMP_NTZ,
    is_current       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS dim_carrier (
    carrier_sk       NUMBER AUTOINCREMENT PRIMARY KEY,
    carrier_id       VARCHAR(64) UNIQUE NOT NULL,
    name             VARCHAR(256),
    sla_tier         VARCHAR(16)
);

CREATE TABLE IF NOT EXISTS dim_time (
    date_key         DATE PRIMARY KEY,
    year             NUMBER, quarter NUMBER, month NUMBER, day NUMBER,
    day_of_week      NUMBER, is_weekend BOOLEAN, is_holiday BOOLEAN
);

-- ============================================================
-- FACTS
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_order (
    order_id              VARCHAR(64) PRIMARY KEY,
    supplier_sk           NUMBER,
    warehouse_sk          NUMBER,
    product_sk            NUMBER,
    order_date_key        DATE,
    requested_delivery_key DATE,
    actual_delivery_key   DATE,
    quantity_ordered      NUMBER,
    quantity_shipped      NUMBER,
    unit_price            DECIMAL(18, 4),
    currency              CHAR(3),
    status                VARCHAR(16),
    source_system         VARCHAR(32),
    loaded_at             TIMESTAMP_TZ
) CLUSTER BY (order_date_key);

CREATE TABLE IF NOT EXISTS fact_shipment (
    shipment_id           VARCHAR(64) PRIMARY KEY,
    order_id              VARCHAR(64),
    carrier_sk            NUMBER,
    origin_warehouse_sk   NUMBER,
    destination_zip       VARCHAR(20),
    shipped_at            TIMESTAMP_TZ,
    expected_delivery_key DATE,
    actual_delivery_key   DATE,
    is_on_time            BOOLEAN,
    is_in_full            BOOLEAN,
    weight_kg             DECIMAL(18, 4),
    source_system         VARCHAR(32)
);

CREATE TABLE IF NOT EXISTS fact_telemetry (
    reading_id            VARCHAR(64) PRIMARY KEY,
    device_id             VARCHAR(64),
    shipment_id           VARCHAR(64),
    reading_timestamp     TIMESTAMP_TZ,
    temperature_c         DECIMAL(7, 3),
    humidity_pct          DECIMAL(5, 2),
    latitude              DECIMAL(9, 6),
    longitude             DECIMAL(9, 6),
    shock_g               DECIMAL(5, 2),
    battery_pct           DECIMAL(5, 2),
    is_cold_chain_breach  BOOLEAN
) CLUSTER BY (reading_timestamp);

CREATE TABLE IF NOT EXISTS fact_weather (
    weather_id            VARCHAR(64) PRIMARY KEY,
    location_id           VARCHAR(64),
    snapshot_timestamp    TIMESTAMP_TZ,
    temp_c                DECIMAL(7, 3),
    humidity_pct          DECIMAL(5, 2),
    wind_kmh              DECIMAL(5, 2),
    precip_mm             DECIMAL(5, 2),
    condition             VARCHAR(32)
);
