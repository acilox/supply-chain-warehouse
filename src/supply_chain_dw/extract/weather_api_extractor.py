"""OpenWeather API extractor."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from supply_chain_dw.config import get_logger, get_settings
from supply_chain_dw.models import WeatherSnapshot

logger = get_logger(__name__)


class WeatherAPIExtractor:
    """Fetches current weather from OpenWeatherMap."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = httpx.Client(timeout=30.0)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._client.close()

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, max=30),
    )
    def fetch(self, lat: float, lon: float, location_id: str) -> WeatherSnapshot:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.settings.openweather_api_key.get_secret_value(),
            "units": "metric",
        }
        resp = self._client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        return WeatherSnapshot(
            location_id=location_id,
            timestamp=datetime.now(tz=UTC),
            temp_c=data["main"]["temp"],
            humidity_pct=data["main"]["humidity"],
            wind_kmh=data["wind"]["speed"] * 3.6,  # m/s -> km/h
            condition=data["weather"][0]["main"],
            precip_mm=data.get("rain", {}).get("1h", 0.0),
        )
