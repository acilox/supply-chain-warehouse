"""MQTT telemetry subscriber.

Subscribes to topic patterns, parses JSON payloads into TelemetryReading,
and pushes them to a callback (e.g., write to S3/DuckDB).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime

from supply_chain_dw.config import get_logger, get_settings
from supply_chain_dw.models import TelemetryReading

logger = get_logger(__name__)


class MQTTTelemetryExtractor:
    """Subscribe to IoT telemetry topics and dispatch readings."""

    def __init__(self, on_reading: Callable[[TelemetryReading], None] | None = None) -> None:
        self.settings = get_settings()
        self.on_reading = on_reading or self._default_handler
        self._client = None

    def __enter__(self):
        self._connect()
        return self

    def __exit__(self, *_):
        self.close()

    def _connect(self) -> None:
        try:
            import paho.mqtt.client as mqtt  # type: ignore[import-not-found]
        except ImportError as e:
            raise RuntimeError("paho-mqtt not installed") from e

        self._client = mqtt.Client(client_id="supply_chain_dw-etl", clean_session=True)
        self._client.username_pw_set(
            self.settings.mqtt_user,
            self.settings.mqtt_password.get_secret_value(),
        )
        self._client.on_message = self._on_message
        self._client.connect(self.settings.mqtt_host, self.settings.mqtt_port, 60)
        self._client.subscribe(self.settings.mqtt_topic_telemetry, qos=1)
        logger.info("mqtt_subscribed", topic=self.settings.mqtt_topic_telemetry)

    def close(self) -> None:
        if self._client is not None:
            self._client.disconnect()
            self._client = None

    def run(self, max_messages: int | None = None) -> int:
        assert self._client is not None
        self._max = max_messages
        self._count = 0
        self._client.loop_forever()
        return self._count

    def _on_message(self, client, userdata, msg) -> None:
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            reading = TelemetryReading(
                device_id=payload["device_id"],
                shipment_id=payload.get("shipment_id"),
                timestamp=datetime.fromisoformat(payload["timestamp"]),
                temperature_c=payload.get("temperature_c"),
                humidity_pct=payload.get("humidity_pct"),
                latitude=payload.get("latitude"),
                longitude=payload.get("longitude"),
                shock_g=payload.get("shock_g"),
                battery_pct=payload.get("battery_pct"),
            )
            self.on_reading(reading)
            self._count += 1
            if self._max and self._count >= self._max:
                client.disconnect()
        except Exception as e:
            logger.warning("mqtt_msg_failed", error=str(e), topic=msg.topic)

    @staticmethod
    def _default_handler(reading: TelemetryReading) -> None:
        logger.debug("telemetry", device=reading.device_id, temp=reading.temperature_c)
