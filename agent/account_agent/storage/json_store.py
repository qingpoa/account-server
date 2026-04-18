from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from .models import BillRecord


class JsonLedgerStore:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._lock = Lock()
        self._ensure_file()

    @property
    def path(self) -> Path:
        return self._path

    def append_bill(self, bill: BillRecord) -> BillRecord:
        with self._lock:
            data = self._read_data()
            data["bills"].append(bill.to_dict())
            self._write_data(data)
        return bill

    def list_bills(self) -> list[BillRecord]:
        data = self._read_data()
        return [BillRecord.from_dict(item) for item in data["bills"]]

    def _ensure_file(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write_data({"bills": []})

    def _read_data(self) -> dict[str, list[dict[str, object]]]:
        self._ensure_file()
        with self._path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _write_data(self, data: dict[str, list[dict[str, object]]]) -> None:
        with self._path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
