# supply-chain-warehouse

A reference implementation of a Kimball-style supply-chain data
warehouse on Snowflake. Consolidates orders from SAP HANA, warehouse
picking activity from Oracle WMS, IoT shipment telemetry over MQTT and
external weather and carrier APIs into conformed facts and SCD-2
dimensions, with a KPI computation layer on top.

## Problem domain

Supply-chain operations require a single analytical surface across ERP,
WMS, in-transit telemetry, and third-party signals (weather, carrier
tracking) to answer questions like on-time-in-full, fill rate, and
lane-level performance. The patterns here cover the Kimball build:
conformed dimensions across order and shipment grain, SCD-2 history for
slow-moving attributes, IoT windowed aggregation, and a KPI engine that
operates on the resulting marts.

## Sources and targets

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
  extract/       sap_hana, oracle_wms (interface stub), mqtt,
                 weather_api, carrier_api (interface stub)
  transform/     scd2 builder, iot_processor (windowed + zscore +
                 cold-chain), kpi_engine, forecasting feature builder
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

## KPIs

| KPI                | formula                                                |
| ------------------ | ------------------------------------------------------ |
| OTIF               | % orders delivered on-or-before due date AND in full   |
| Fill rate          | sum(qty_shipped) / sum(qty_ordered)                    |
| Avg lead time      | mean(actual_delivery - order_date) for delivered rows  |
| Backorder rate     | % of orders where qty_shipped < qty_ordered            |

`kpi_engine.py` operates on DataFrames so the same functions work in
notebooks for ad-hoc analysis.

## IoT

`IoTProcessor` provides:

- pandas `resample` aggregation by device and time window (1m / 5m / 1h)
- cold-chain breach detection against a configurable temperature range
  (default 2–8 °C for pharma)
- z-score anomaly detection with a configurable threshold (default 2.5σ)

The sample telemetry CSV includes a deliberate breach so the alert
path can be exercised end-to-end with `make run-sample`.

## DAG generation

Airflow DAGs are generated from `config/sources.yaml`. Adding a new
source entry and restarting the scheduler exposes a new DAG. The
factory is intentionally simple (extract → transform → load); per-source
specialisation lives in the operators themselves.

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

## Design notes

- The Oracle WMS extractor is provided as an interface stub. Real WMS
  deployments typically use a hand-written SQL view targeting the
  specific tables in use; the interface is shaped so the extractor
  drops in without changes elsewhere.
- The forecasting feature builder produces lag, rolling, and calendar
  features and exposes them as a flat DataFrame. A demand model (e.g.
  XGBoost, Prophet, or a deep model) sits downstream and is intentionally
  out of scope for this repo.
- The FedEx tracking integration is stubbed. Production deployments
  typically substitute a tracking aggregator (e.g. AfterShip,
  ShipEngine) to avoid maintaining N carrier auth flows.

## About this code

Open-source companion to the supply-chain data work done by
[acilox](https://github.com/acilox). For paid implementation, dimensional
modelling, or extension of these patterns into a production environment,
open an issue.
