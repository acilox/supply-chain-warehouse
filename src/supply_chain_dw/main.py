"""Supply Chain DW CLI."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from supply_chain_dw.config import configure_logging, get_logger, get_settings
from supply_chain_dw.transform import (
    ForecastingFeatureBuilder,
    IoTProcessor,
    KPIEngine,
)

app = typer.Typer(name="supply_chain_dw", help="Supply Chain DW CLI", no_args_is_help=True)
console = Console()
logger = get_logger(__name__)


def _bootstrap() -> None:
    s = get_settings()
    configure_logging(s.log_level, s.log_format)


@app.command()
def run(source: str = typer.Option("sample", help="Source (sample|sap|wms|iot|all)")) -> None:
    """Run the demo pipeline against sample CSVs."""
    _bootstrap()

    pkg_dir = Path(__file__).resolve().parent.parent.parent
    orders_path = pkg_dir / "data" / "sample" / "orders.csv"
    telemetry_path = pkg_dir / "data" / "sample" / "telemetry.csv"

    if not orders_path.exists():
        orders_path = Path("data/sample/orders.csv")
        telemetry_path = Path("data/sample/telemetry.csv")

    orders_df = pd.read_csv(
        orders_path, parse_dates=["order_date", "requested_delivery", "actual_delivery"]
    )
    telemetry_df = pd.read_csv(telemetry_path, parse_dates=["timestamp"])

    # KPIs
    kpis = KPIEngine().all_kpis(orders_df)
    table = Table(title="Supply Chain KPIs")
    table.add_column("KPI", style="cyan")
    table.add_column("Value", justify="right", style="green")
    for k, v in kpis.items():
        if isinstance(v, float):
            table.add_row(k, f"{v:.2f}")
        else:
            table.add_row(k, str(v))
    console.print(table)

    # IoT
    iot = IoTProcessor()
    agg = iot.windowed_aggregate(telemetry_df, window="5min")
    console.print(f"\n[bold]IoT aggregated rows:[/] {len(agg)}")
    breaches = 0
    from supply_chain_dw.models import TelemetryReading

    for _, row in telemetry_df.iterrows():
        r = TelemetryReading(
            device_id=row["device_id"],
            shipment_id=row.get("shipment_id") if pd.notna(row.get("shipment_id")) else None,
            timestamp=row["timestamp"].to_pydatetime(),
            temperature_c=row.get("temperature_c") if pd.notna(row.get("temperature_c")) else None,
            humidity_pct=row.get("humidity_pct") if pd.notna(row.get("humidity_pct")) else None,
        )
        if iot.detect_cold_chain_breach(r):
            breaches += 1
    console.print(f"[red]Cold-chain breaches detected: {breaches}[/]")

    # Forecasting features (demo on a slice)
    demand = (
        orders_df.groupby([pd.Grouper(key="order_date", freq="D"), "product_id"])[
            "quantity_ordered"
        ]
        .sum()
        .reset_index()
        .rename(columns={"order_date": "demand_date", "quantity_ordered": "quantity"})
    )
    features = ForecastingFeatureBuilder().build(demand)
    console.print(
        f"\n[bold]Forecasting feature rows:[/] {len(features)}  "
        f"[bold]columns:[/] {features.shape[1]}"
    )


if __name__ == "__main__":
    app()
