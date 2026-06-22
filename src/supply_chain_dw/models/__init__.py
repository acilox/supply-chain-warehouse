"""Pydantic models for supply-chain domain."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PICKING = "PICKING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class Order(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    order_id: str = Field(..., max_length=64)
    customer_id: str = Field(..., max_length=64)
    supplier_id: str = Field(..., max_length=64)
    warehouse_id: str = Field(..., max_length=64)
    product_id: str = Field(..., max_length=64)
    quantity_ordered: int = Field(..., ge=1)
    quantity_shipped: int = Field(..., ge=0)
    unit_price: Decimal = Field(..., ge=0)
    currency: str = Field("USD", max_length=3)
    order_date: date
    requested_delivery: date
    actual_delivery: date | None = None
    status: OrderStatus = OrderStatus.PENDING
    source_system: str
    extracted_at: datetime


class Shipment(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    shipment_id: str
    order_id: str
    carrier_id: str
    tracking_number: str | None = None
    origin_warehouse: str
    destination_zip: str
    weight_kg: Decimal | None = None
    shipped_at: datetime
    expected_delivery: date
    actual_delivery: date | None = None
    is_on_time: bool | None = None
    is_in_full: bool | None = None
    source_system: str
    extracted_at: datetime


class Supplier(BaseModel):
    """SCD Type 2 supplier dimension."""

    supplier_id: str
    name: str
    country: str
    city: str | None = None
    quality_tier: str = "STANDARD"
    contract_terms_days: int = 30
    effective_from: datetime
    effective_to: datetime | None = None
    is_current: bool = True


class TelemetryReading(BaseModel):
    """IoT sensor reading from MQTT."""

    model_config = ConfigDict(str_strip_whitespace=True)

    device_id: str
    shipment_id: str | None = None
    timestamp: datetime
    temperature_c: float | None = None
    humidity_pct: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    shock_g: float | None = None
    battery_pct: float | None = None


class WeatherSnapshot(BaseModel):
    """OpenWeather one-call snapshot."""

    location_id: str
    timestamp: datetime
    temp_c: float
    humidity_pct: float
    wind_kmh: float
    condition: str
    precip_mm: float = 0.0
