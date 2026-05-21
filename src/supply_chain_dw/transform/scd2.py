"""SCD Type 2 builder — produces the staging-to-dim MERGE plan."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from supply_chain_dw.config import get_logger

logger = get_logger(__name__)


class SCD2Builder:
    """Compares incoming records against current MPI/dim and tags rows for SCD2 MERGE.

    Output schema:
        - new_records: rows to insert as is_current=TRUE
        - expiring_records: existing rows to close out (set effective_to=now, is_current=FALSE)
        - unchanged_records: no-op
    """

    def __init__(self, key_col: str = "supplier_id", tracked_cols: list[str] | None = None) -> None:
        self.key_col = key_col
        self.tracked_cols = tracked_cols or ["name", "country", "city", "quality_tier"]

    def diff(self, incoming: pd.DataFrame, current_dim: pd.DataFrame) -> dict[str, pd.DataFrame]:
        if incoming.empty:
            return {
                "new_records": pd.DataFrame(),
                "expiring_records": pd.DataFrame(),
                "unchanged_records": pd.DataFrame(),
            }

        # Filter current_dim to is_current=True rows
        if "is_current" in current_dim.columns:
            current_dim = current_dim[current_dim["is_current"]]

        if current_dim.empty:
            new = incoming.copy()
            new["effective_from"] = datetime.utcnow()
            new["effective_to"] = None
            new["is_current"] = True
            return {
                "new_records": new,
                "expiring_records": pd.DataFrame(),
                "unchanged_records": pd.DataFrame(),
            }

        merged = incoming.merge(
            current_dim,
            on=self.key_col,
            how="left",
            suffixes=("_new", "_current"),
        )

        changed_mask = pd.Series(False, index=merged.index)
        for col in self.tracked_cols:
            new_col = f"{col}_new" if f"{col}_new" in merged.columns else col
            cur_col = f"{col}_current" if f"{col}_current" in merged.columns else col
            if new_col in merged.columns and cur_col in merged.columns:
                changed_mask = changed_mask | (merged[new_col] != merged[cur_col])

        new_keys = merged[merged[f"{self.tracked_cols[0]}_current"].isna()][self.key_col].unique() \
            if f"{self.tracked_cols[0]}_current" in merged.columns else []
        changed_keys = merged[changed_mask & merged[f"{self.tracked_cols[0]}_current"].notna()][self.key_col].unique() \
            if f"{self.tracked_cols[0]}_current" in merged.columns else []

        new_records = incoming[incoming[self.key_col].isin(list(new_keys) + list(changed_keys))].copy()
        new_records["effective_from"] = datetime.utcnow()
        new_records["effective_to"] = None
        new_records["is_current"] = True

        expiring_records = current_dim[current_dim[self.key_col].isin(list(changed_keys))].copy()
        if not expiring_records.empty:
            expiring_records["effective_to"] = datetime.utcnow()
            expiring_records["is_current"] = False

        unchanged = incoming[
            ~incoming[self.key_col].isin(list(new_keys) + list(changed_keys))
        ].copy()

        logger.info(
            "scd2_diff_complete",
            new=len(new_records),
            expiring=len(expiring_records),
            unchanged=len(unchanged),
        )
        return {
            "new_records": new_records,
            "expiring_records": expiring_records,
            "unchanged_records": unchanged,
        }
