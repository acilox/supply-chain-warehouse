"""Supply chain KPI engine — OTIF, fill rate, lead time, etc."""

from __future__ import annotations

from datetime import date

import pandas as pd

from supply_chain_dw.config import get_logger

logger = get_logger(__name__)


class KPIEngine:
    """Computes core supply-chain KPIs from order + shipment DataFrames."""

    def otif(self, orders_df: pd.DataFrame) -> float:
        """On-Time In-Full: % orders delivered on/before due date AND fully shipped."""
        if orders_df.empty:
            return 0.0
        delivered = orders_df[orders_df["actual_delivery"].notna()]
        if delivered.empty:
            return 0.0
        on_time = pd.to_datetime(delivered["actual_delivery"]) <= pd.to_datetime(
            delivered["requested_delivery"]
        )
        in_full = delivered["quantity_shipped"] >= delivered["quantity_ordered"]
        return (on_time & in_full).mean() * 100.0

    def fill_rate(self, orders_df: pd.DataFrame) -> float:
        """% of ordered quantity actually shipped."""
        if orders_df.empty or orders_df["quantity_ordered"].sum() == 0:
            return 0.0
        return orders_df["quantity_shipped"].sum() / orders_df["quantity_ordered"].sum() * 100.0

    def avg_lead_time_days(self, orders_df: pd.DataFrame) -> float:
        delivered = orders_df[orders_df["actual_delivery"].notna()]
        if delivered.empty:
            return 0.0
        lead = (
            pd.to_datetime(delivered["actual_delivery"]) - pd.to_datetime(delivered["order_date"])
        ).dt.days
        return float(lead.mean())

    def backorder_rate(self, orders_df: pd.DataFrame) -> float:
        if orders_df.empty:
            return 0.0
        backorders = orders_df[orders_df["quantity_shipped"] < orders_df["quantity_ordered"]]
        return len(backorders) / len(orders_df) * 100.0

    def all_kpis(self, orders_df: pd.DataFrame, as_of: date | None = None) -> dict[str, float]:
        result = {
            "otif_pct": self.otif(orders_df),
            "fill_rate_pct": self.fill_rate(orders_df),
            "avg_lead_time_days": self.avg_lead_time_days(orders_df),
            "backorder_rate_pct": self.backorder_rate(orders_df),
            "as_of": (as_of or date.today()).isoformat(),
        }
        logger.info("kpis_computed", **result)
        return result
