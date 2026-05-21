"""Tests for KPIEngine."""

from __future__ import annotations

import pandas as pd

from supply_chain_dw.transform import KPIEngine


def make_orders():
    return pd.DataFrame(
        {
            "order_id": ["A", "B", "C", "D"],
            "quantity_ordered": [100, 100, 100, 100],
            "quantity_shipped": [100, 100, 50, 100],
            "order_date": ["2026-05-01", "2026-05-01", "2026-05-02", "2026-05-02"],
            "requested_delivery": ["2026-05-05", "2026-05-05", "2026-05-05", "2026-05-05"],
            "actual_delivery": ["2026-05-04", "2026-05-06", "2026-05-05", None],
        }
    )


def test_otif():
    e = KPIEngine()
    df = make_orders()
    # A: on-time + full; B: late + full; C: on-time but short; D: not delivered
    # Among delivered (A,B,C): only A meets OTIF -> 1/3 = 33.33%
    assert abs(e.otif(df) - 33.33) < 0.1


def test_fill_rate():
    e = KPIEngine()
    df = make_orders()
    # Total ordered=400, total shipped=350 → 87.5%
    assert abs(e.fill_rate(df) - 87.5) < 0.1


def test_avg_lead_time():
    e = KPIEngine()
    df = make_orders()
    avg = e.avg_lead_time_days(df)
    # A: 3 days, B: 5 days, C: 3 days → avg ~3.67
    assert 3 <= avg <= 5


def test_backorder_rate():
    e = KPIEngine()
    df = make_orders()
    # 1 of 4 has short ship → 25%
    assert e.backorder_rate(df) == 25.0
