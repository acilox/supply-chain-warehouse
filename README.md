# supply-chain-warehouse

A Kimball-style data warehouse built on Snowflake that consolidates
orders (SAP HANA), warehouse picking activity (Oracle WMS), IoT telemetry
(MQTT) and external weather/carrier APIs into facts and SCD-2 dimensions,
with a KPI layer on top.

## Problem

The supply-chain ops team wanted one place to answer: are we shipping
on-time? Where is OTIF dropping? Which lanes are most affected by
weather? The data lived in five places. This is the pipeline that joins
them.

## Sources & targets

```
sources                          targets
-------                          -------
SAP HANA (ERP orders)        --> snowflake (fact_order, fact_shipment,
oracle WMS (picking)         -->            fact_telemetry, fact_weather,
mqtt (truck sensors)         -->            dim_supplier [SCD-2],
openweathermap.org           -->            dim_warehouse [SCD-2],
fedex/ups tracking APIs      -->            dim_product [SCD-2],
                                 +--      dim_carrier, dim_time)
                                 |
                                 +-> s3 (raw + curated zones)
                                 +-> postgres (metrics for grafana)
```

## Layout

```
src/supply_chain_dw/
  config/        settings + logging
  extract/       sap_hana, oracle_wms (TODO), mqtt, weather_api,
                 carrier_api (TODO)
  transform/     scd2 (dim builder), iot_processor (windowed +
                 zscore + cold-chain), kpi_engine, forecasting
  load/          snowflake_loader (write_pandas + MERGE)
  orchestration/ dag_factory.py — Airflow DAGs from config/sources.yaml
  models/        Order, Shipment, Supplier, TelemetryReading,
                 WeatherSnapshot
  main.py        Typer CLI (`run --source sample`)

config/sources.yaml   per-source schedule + table mapping (read by the
                      DAG factory at parse time)
sql/ddl/              snowflake_starschema.sql (full DDL)
data/sample/          orders.csv (12 rows), telemetry.csv (15 readings,
                      one cold-chain breach)
```

## KPIs implemented

| KPI                | formula                                                |
| ------------------ | ------------------------------------------------------ |
| OTIF               | % orders delivered on-or-before due date AND in full   |
| Fill rate          | sum(qty_shipped) / sum(qty_ordered)                    |
| Avg lead time      | mean(actual_delivery - order_date) for delivered rows  |
| Backorder rate     | % of orders where qty_shipped < qty_ordered            |

The functions in `kpi_engine.py` take a DataFrame, so you can drop them
into a notebook for ad-hoc slicing.

## IoT

`IoTProcessor` does:

- pandas `resample` aggregation by device + window (1m / 5m / 1h)
- cold-chain breach detection on `temperature_c` against the configured
  min/max (defaults to 2-8 °C for pharma)
- z-score anomaly detection with a configurable threshold (default 2.5σ)

The sample telemetry CSV includes an obvious breach around 08:25 so you
can see the alert path fire end-to-end with `make run-sample`.

## DAG generation

Airflow DAGs are generated dynamically from `config/sources.yaml`. Add a
new source there, restart the scheduler, and it shows up in the UI. The
DAG factory is intentionally simple (extract → transform → load
sequence) — the per-source work happens in the right operators.

## Running locally

```
cp .env.example .env
make install
make docker-up         # postgres, mosquitto (mqtt), minio
make run-sample        # runs CLI demo with included CSVs
make build-warehouse   # prints the Snowflake DDL for review
```

## Stack

Python 3.11, snowflake-connector-python, snowflake-sqlalchemy,
oracledb, hdbcli (SAP HANA), paho-mqtt, httpx + tenacity, boto3,
pandas, polars, pyarrow, holidays, pydantic, structlog, Airflow 2.x.

## Open items

- The Oracle WMS extractor is stubbed (we used a hand-written SQL view
  in production). Drop-in replacement needed before this runs against a
  real WMS.
- The forecasting feature builder produces lag/rolling features and a
  US holiday flag, but the actual demand model lives in a separate ML
  repo. There's a clean interface — `ForecastingFeatureBuilder.build()`
  returns a DataFrame the model can take directly.
- We never finished the FedEx tracking integration; the auth flow is
  fiddly and we ended up using a third-party aggregator instead.
