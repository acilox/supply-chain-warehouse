"""IoT telemetry processor with windowed aggregation + anomaly detection."""

from __future__ import annotations

from statistics import mean, pstdev

import pandas as pd

from supply_chain_dw.config import get_logger, get_settings
from supply_chain_dw.models import TelemetryReading

logger = get_logger(__name__)


class IoTProcessor:
    """Aggregates and scores IoT telemetry events."""

    def __init__(self) -> None:
        s = get_settings()
        self.temp_min = s.telemetry_temp_min_c
        self.temp_max = s.telemetry_temp_max_c
        self.zscore_threshold = s.telemetry_anomaly_zscore

    def windowed_aggregate(self, readings_df: pd.DataFrame, window: str = "5min") -> pd.DataFrame:
        """Resample by device + window. Returns mean/min/max per metric."""
        if readings_df.empty:
            return pd.DataFrame()
        df = readings_df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        agg = (
            df.set_index("timestamp")
            .groupby("device_id")
            .resample(window)
            .agg(
                {
                    "temperature_c": ["mean", "min", "max"],
                    "humidity_pct": ["mean", "min", "max"],
                    "shock_g": ["max"],
                }
            )
            .reset_index()
        )
        # Flatten MultiIndex columns
        agg.columns = ["_".join(filter(None, col)).strip("_") for col in agg.columns]
        return agg

    def detect_cold_chain_breach(self, reading: TelemetryReading) -> dict | None:
        """Returns an alert dict if the reading breaches the cold-chain range."""
        if reading.temperature_c is None:
            return None
        if reading.temperature_c < self.temp_min or reading.temperature_c > self.temp_max:
            alert = {
                "device_id": reading.device_id,
                "shipment_id": reading.shipment_id,
                "timestamp": reading.timestamp.isoformat(),
                "metric": "temperature_c",
                "value": reading.temperature_c,
                "min_allowed": self.temp_min,
                "max_allowed": self.temp_max,
                "severity": "CRITICAL",
            }
            logger.error("cold_chain_breach", **alert)
            return alert
        return None

    def detect_anomaly_zscore(
        self, readings: list[TelemetryReading], field: str = "temperature_c"
    ) -> list[dict]:
        """Z-score anomaly detection on a single metric."""
        values = [getattr(r, field) for r in readings if getattr(r, field) is not None]
        if len(values) < 5:
            return []
        mu = mean(values)
        sigma = pstdev(values)
        if sigma == 0:
            return []
        anomalies = []
        for r in readings:
            v = getattr(r, field)
            if v is None:
                continue
            z = abs((v - mu) / sigma)
            if z >= self.zscore_threshold:
                anomalies.append(
                    {
                        "device_id": r.device_id,
                        "timestamp": r.timestamp.isoformat(),
                        "metric": field,
                        "value": v,
                        "z_score": round(z, 2),
                    }
                )
        if anomalies:
            logger.warning("iot_anomalies_detected", count=len(anomalies), field=field)
        return anomalies
