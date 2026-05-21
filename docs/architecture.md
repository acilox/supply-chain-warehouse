# Supply Chain DW Architecture

## Star Schema (Kimball)

```mermaid
erDiagram
    fact_order ||--o{ dim_supplier : "supplier_sk"
    fact_order ||--o{ dim_warehouse : "warehouse_sk"
    fact_order ||--o{ dim_product : "product_sk"
    fact_order ||--o{ dim_time : "order_date_key"

    fact_shipment ||--o{ dim_carrier : "carrier_sk"
    fact_shipment ||--o{ dim_warehouse : "origin_warehouse_sk"
    fact_shipment ||--o{ dim_time : "shipped_at"

    fact_telemetry ||--o{ fact_shipment : "shipment_id"
    fact_weather ||--o{ dim_warehouse : "location_id"

    dim_supplier {
        number supplier_sk
        string supplier_id
        string name
        boolean is_current
    }
    dim_warehouse {
        number warehouse_sk
        string warehouse_id
        boolean is_current
    }
    dim_product {
        number product_sk
        string product_id
        boolean is_current
    }
```

## Data Quality Gates
Between every pipeline stage, a DQ gate verifies:
- Row counts ratio between input/output (alert if < 0.95 or > 1.05)
- Null rate per critical column < 1%
- Surrogate key resolution rate = 100% (no orphan dims)

## Operational SLAs
| Metric | Target |
|--------|--------|
| Pipeline latency | < 30 min for incremental loads |
| OTIF refresh | T+1 day |
| IoT alert latency | < 5 min |
