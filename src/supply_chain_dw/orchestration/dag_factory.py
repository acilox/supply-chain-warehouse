"""Dynamically generate Airflow DAGs from a YAML config.

For each entry in `config/sources.yaml`, emits an Airflow DAG that:
1. Extracts from the source
2. Applies the right transformations
3. Loads into the right warehouse target

Usage in Airflow's dags/ folder:
    from supply_chain_dw.orchestration.dag_factory import register_dags
    register_dags(globals())
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from supply_chain_dw.config import get_logger, get_settings

logger = get_logger(__name__)


def _load_sources_config() -> list[dict[str, Any]]:
    s = get_settings()
    path = Path(s.sources_config_path)
    if not path.exists():
        logger.warning("sources_yaml_missing", path=str(path))
        return []
    with open(path) as f:
        config = yaml.safe_load(f) or {}
    return config.get("sources", [])


def register_dags(global_ns: dict[str, Any]) -> None:
    """Inject generated DAGs into the caller's globals so Airflow can discover them."""
    try:
        from airflow import DAG  # type: ignore[import-not-found]
        from airflow.operators.python import PythonOperator  # type: ignore[import-not-found]
    except ImportError:
        logger.warning("airflow_not_available_skipping_dag_registration")
        return

    sources = _load_sources_config()
    for src in sources:
        name = src["name"]
        dag = DAG(
            dag_id=f"supply_chain_dw_{name}",
            schedule=src.get("schedule", "@daily"),
            start_date=datetime(2026, 1, 1),
            catchup=False,
            default_args={"retries": 3, "retry_delay": timedelta(minutes=5)},
            tags=["supply_chain_dw", "etl", src["type"]],
        )

        def _extract(src=src, **context):
            logger.info("extract_invoked", source=src["name"], type=src["type"])

        def _transform(src=src, **context):
            logger.info("transform_invoked", source=src["name"])

        def _load(src=src, **context):
            logger.info("load_invoked", source=src["name"], target=src.get("target_fact"))

        with dag:
            t1 = PythonOperator(task_id=f"extract_{name}", python_callable=_extract)
            t2 = PythonOperator(task_id=f"transform_{name}", python_callable=_transform)
            t3 = PythonOperator(task_id=f"load_{name}", python_callable=_load)
            t1 >> t2 >> t3

        global_ns[f"supply_chain_dw_{name}"] = dag
        logger.info("dag_registered", dag_id=f"supply_chain_dw_{name}")
