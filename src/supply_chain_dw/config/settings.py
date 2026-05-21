"""Supply Chain DW Pydantic settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "json"

    # SAP HANA
    sap_host: str = "sap.example.com"
    sap_port: int = 30015
    sap_user: str = "supply_chain_dw_reader"
    sap_password: SecretStr = SecretStr("__PLACEHOLDER__")

    # Oracle WMS
    oracle_host: str = "wms.example.com"
    oracle_port: int = 1521
    oracle_service_name: str = "WMSPROD"
    oracle_user: str = "supply_chain_dw_reader"
    oracle_password: SecretStr = SecretStr("__PLACEHOLDER__")

    # Snowflake
    snowflake_account: str = "abc12345.us-east-1"
    snowflake_user: str = "supply_chain_dw_etl"
    snowflake_password: SecretStr = SecretStr("__PLACEHOLDER__")
    snowflake_warehouse: str = "SUPPLY_CHAIN_WH"
    snowflake_database: str = "SUPPLY_CHAIN_DW"
    snowflake_schema: str = "PUBLIC"

    # AWS S3
    aws_access_key_id: SecretStr = SecretStr("__PLACEHOLDER__")
    aws_secret_access_key: SecretStr = SecretStr("__PLACEHOLDER__")
    aws_region: str = "us-east-1"
    s3_bucket: str = "supply_chain_dw-lake"
    s3_raw_prefix: str = "raw/"
    s3_curated_prefix: str = "curated/"

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "supply_chain_dw_metrics"
    postgres_user: str = "supply_chain_dw"
    postgres_password: SecretStr = SecretStr("__PLACEHOLDER__")

    # MQTT
    mqtt_host: str = "mqtt.example.com"
    mqtt_port: int = 1883
    mqtt_user: str = "supply_chain_dw"
    mqtt_password: SecretStr = SecretStr("__PLACEHOLDER__")
    mqtt_topic_telemetry: str = "supply_chain_dw/telemetry/+"

    # APIs
    openweather_api_key: SecretStr = SecretStr("__PLACEHOLDER__")
    fedex_api_key: SecretStr = SecretStr("__PLACEHOLDER__")
    ups_api_key: SecretStr = SecretStr("__PLACEHOLDER__")

    # Pipeline
    pipeline_batch_size: int = 5000
    sources_config_path: str = "config/sources.yaml"

    # IoT thresholds
    telemetry_temp_min_c: float = 2.0
    telemetry_temp_max_c: float = 8.0
    telemetry_anomaly_zscore: float = 2.5

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:"
            f"{self.postgres_password.get_secret_value()}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
