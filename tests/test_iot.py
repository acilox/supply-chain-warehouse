"""Tests for IoTProcessor."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from supply_chain_dw.models import TelemetryReading
from supply_chain_dw.transform import IoTProcessor


def make_reading(temp: float) -> TelemetryReading:
    return TelemetryReading(
        device_id="DEV-1",
        timestamp=datetime.now(tz=UTC),
        temperature_c=temp,
    )


def test_cold_chain_breach_above_max():
    p = IoTProcessor()
    alert = p.detect_cold_chain_breach(make_reading(15.0))
    assert alert is not None
    assert alert["severity"] == "CRITICAL"


def test_cold_chain_breach_below_min():
    p = IoTProcessor()
    alert = p.detect_cold_chain_breach(make_reading(-2.0))
    assert alert is not None


def test_cold_chain_normal():
    p = IoTProcessor()
    alert = p.detect_cold_chain_breach(make_reading(5.0))
    assert alert is None


def test_zscore_detection():
    p = IoTProcessor()
    # 10 normal + 1 huge anomaly
    base_time = datetime.now(tz=UTC)
    readings = [
        TelemetryReading(
            device_id="D", timestamp=base_time + timedelta(seconds=i), temperature_c=5.0
        )
        for i in range(10)
    ]
    readings.append(
        TelemetryReading(
            device_id="D", timestamp=base_time + timedelta(seconds=60), temperature_c=50.0
        )
    )
    anomalies = p.detect_anomaly_zscore(readings)
    assert len(anomalies) >= 1
