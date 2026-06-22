"""Snowflake star-schema loader (facts + SCD2 dims)."""

from __future__ import annotations

import pandas as pd

from supply_chain_dw.config import get_logger, get_settings

logger = get_logger(__name__)


class SnowflakeStarSchemaLoader:
    """Loads fact + dim DataFrames into the Snowflake star schema."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._conn = None

    def __enter__(self):
        self._connect()
        return self

    def __exit__(self, *_):
        self.close()

    def _connect(self) -> None:
        try:
            import snowflake.connector  # type: ignore[import-not-found]
        except ImportError as e:
            raise RuntimeError("snowflake-connector-python not installed") from e
        s = self.settings
        self._conn = snowflake.connector.connect(
            account=s.snowflake_account,
            user=s.snowflake_user,
            password=s.snowflake_password.get_secret_value(),
            warehouse=s.snowflake_warehouse,
            database=s.snowflake_database,
            schema=s.snowflake_schema,
        )

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def write_fact(self, df: pd.DataFrame, table: str) -> int:
        if df.empty:
            return 0
        from snowflake.connector.pandas_tools import write_pandas  # type: ignore[import-not-found]

        success, _, nrows, _ = write_pandas(
            self._conn, df, table_name=table.upper(), quote_identifiers=False
        )
        if not success:
            raise RuntimeError(f"write_pandas to {table} failed")
        logger.info("snowflake_fact_loaded", table=table, rows=nrows)
        return nrows
