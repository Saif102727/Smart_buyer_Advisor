"""تخزين تاريخ الأسعار (SQLite) — استعلامات مُعلَّمة فقط (لا SQL injection) واتصالات تُغلق دائماً."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pandas as pd

from .logs import get_logger

log = get_logger("storage")


class PriceRepository:
    MAX_ROWS_PER_SAVE = 200

    def __init__(self, db_path: str, retention_days: int = 180):
        self._path = Path(db_path)
        self._retention = int(retention_days)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS prices("
                "product TEXT NOT NULL, country TEXT NOT NULL, store TEXT NOT NULL, "
                "price REAL NOT NULL, ts TEXT NOT NULL DEFAULT (datetime('now')))")
            c.execute("CREATE INDEX IF NOT EXISTS idx_prices ON prices(product, country, ts)")
        try:
            os.chmod(self._path, 0o600)       # قراءة/كتابة لصاحب العملية فقط
        except OSError:
            pass

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path, timeout=10)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _key(product: str) -> str:
        return product.casefold().strip()[:120]

    def save(self, product: str, country: str, offers: pd.DataFrame) -> None:
        if offers.empty:
            return
        rows = [(self._key(product), country, str(r.store)[:120], float(r.price))
                for r in offers.head(self.MAX_ROWS_PER_SAVE).itertuples()]
        try:
            with self._connect() as c:
                c.executemany("INSERT INTO prices(product, country, store, price) VALUES (?,?,?,?)", rows)
                c.execute("DELETE FROM prices WHERE ts < datetime('now', ?)", (f"-{self._retention} days",))
        except sqlite3.Error as exc:
            log.warning("save failed: %s", type(exc).__name__)

    def history(self, product: str, country: str, limit: int = 2000) -> pd.DataFrame:
        try:
            with self._connect() as c:
                cur = c.execute(
                    "SELECT store, price, ts FROM prices WHERE product=? AND country=? ORDER BY ts DESC LIMIT ?",
                    (self._key(product), country, int(limit)))
                return pd.DataFrame(cur.fetchall(), columns=["store", "price", "ts"])
        except sqlite3.Error as exc:
            log.warning("history failed: %s", type(exc).__name__)
            return pd.DataFrame(columns=["store", "price", "ts"])
