"""Demand-forecasting feature engineering."""

from __future__ import annotations

import pandas as pd

from supply_chain_dw.config import get_logger

logger = get_logger(__name__)


class ForecastingFeatureBuilder:
    """Builds lag/rolling/seasonality features for downstream demand models."""

    LAGS = [1, 7, 14, 30]
    ROLLING_WINDOWS = [7, 14, 30]

    def build(self, daily_demand: pd.DataFrame) -> pd.DataFrame:
        """Given daily demand per product (cols: product_id, demand_date, quantity),
        return augmented features.
        """
        if daily_demand.empty:
            return daily_demand
        df = daily_demand.copy()
        df["demand_date"] = pd.to_datetime(df["demand_date"])
        df = df.sort_values(["product_id", "demand_date"])

        # Lag features
        for lag in self.LAGS:
            df[f"qty_lag_{lag}"] = df.groupby("product_id")["quantity"].shift(lag)

        # Rolling mean & stddev
        for w in self.ROLLING_WINDOWS:
            grp = df.groupby("product_id")["quantity"]
            df[f"qty_rolling_mean_{w}"] = grp.shift(1).rolling(w).mean().values
            df[f"qty_rolling_std_{w}"] = grp.shift(1).rolling(w).std().values

        # Calendar features
        df["dow"] = df["demand_date"].dt.dayofweek
        df["month"] = df["demand_date"].dt.month
        df["is_weekend"] = df["dow"].isin([5, 6]).astype(int)
        df["quarter"] = df["demand_date"].dt.quarter

        # Holiday flag
        try:
            import holidays  # type: ignore[import-not-found]

            us_holidays = holidays.UnitedStates()
            df["is_holiday"] = (
                df["demand_date"].dt.date.apply(lambda d: d in us_holidays).astype(int)
            )
        except ImportError:
            df["is_holiday"] = 0

        logger.info("forecasting_features_built", rows=len(df), features=df.shape[1])
        return df

    def weather_enrich(self, demand_df: pd.DataFrame, weather_df: pd.DataFrame) -> pd.DataFrame:
        """Join weather snapshots into the demand feature table."""
        if demand_df.empty or weather_df.empty:
            return demand_df
        weather_df = weather_df.copy()
        weather_df["date"] = pd.to_datetime(weather_df["timestamp"]).dt.date

        merged = demand_df.merge(
            weather_df[["location_id", "date", "temp_c", "precip_mm", "wind_kmh"]],
            left_on=["warehouse_postal_code", "demand_date"],
            right_on=["location_id", "date"],
            how="left",
        )
        return merged.drop(columns=["date", "location_id"], errors="ignore")
