
from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import BillRecord


class SqliteLedgerStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._ensure_db()

    @property
    def path(self) -> Path:
        return self._db_path

    def append_bill(self, bill: BillRecord) -> BillRecord:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO bills (id, amount, kind, category, note, occurred_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bill.id,
                    bill.amount,
                    bill.kind,
                    bill.category,
                    bill.note,
                    bill.occurred_at,
                    bill.created_at,
                ),
            )
        return bill

    def list_bills(self) -> list[BillRecord]:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM bills").fetchall()
            return [BillRecord.from_dict(dict(row)) for row in rows]

    def _ensure_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bills (
                    id TEXT PRIMARY KEY,
                    amount REAL NOT NULL,
                    kind TEXT NOT NULL,
                    category TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    occurred_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
