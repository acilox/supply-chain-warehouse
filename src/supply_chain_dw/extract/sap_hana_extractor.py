"""SAP HANA extractor."""

from __future__ import annotations

from datetime import datetime
from typing import Iterator

from supply_chain_dw.config import get_logger, get_settings

logger = get_logger(__name__)


ORDER_QUERY = """
SELECT
    VBELN AS order_id, KUNNR AS customer_id, LIFNR AS supplier_id,
    WERKS AS warehouse_id, MATNR AS product_id,
    KWMENG AS quantity_ordered, LMENG AS quantity_shipped,
    NETPR AS unit_price, WAERS AS currency,
    ERDAT AS order_date, EDATU AS requested_delivery
FROM SAPABAP1.VBAK
WHERE ERDAT >= ?
"""


class SAPHANAExtractor:
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
            from hdbcli import dbapi  # type: ignore[import-not-found]
        except ImportError as e:
            raise RuntimeError("hdbcli (SAP HANA driver) not installed") from e
        s = self.settings
        self._conn = dbapi.connect(
            address=s.sap_host,
            port=s.sap_port,
            user=s.sap_user,
            password=s.sap_password.get_secret_value(),
        )
        logger.info("sap_hana_connected")

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def extract_orders(self, since: datetime) -> Iterator[dict]:
        if self._conn is None:
            self._connect()
        assert self._conn is not None
        cur = self._conn.cursor()
        cur.execute(ORDER_QUERY, (since,))
        for row in cur:
            yield {
                "order_id": str(row[0]),
                "customer_id": str(row[1]),
                "supplier_id": str(row[2]),
                "warehouse_id": str(row[3]),
                "product_id": str(row[4]),
                "quantity_ordered": int(row[5]),
                "quantity_shipped": int(row[6] or 0),
                "unit_price": float(row[7]),
                "currency": row[8],
                "order_date": row[9],
                "requested_delivery": row[10],
            }
        cur.close()
