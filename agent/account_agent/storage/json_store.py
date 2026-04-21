from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from .models import BillRecord


class JsonLedgerStore:
    def __init__(self, path: Path) -> None:
        """创建一个基于 JSON 文件的账本存储。"""
        self._path = Path(path)
        self._lock = Lock()
        self._ensure_file()

    @property
    def path(self) -> Path:
        """返回底层 JSON 文件路径。"""
        return self._path

    def append_bill(self, bill: BillRecord) -> BillRecord:
        """向本地 JSON 账本追加一条账单记录。"""
        with self._lock:
            data = self._read_data()
            data["bills"].append(bill.to_dict())
            self._write_data(data)
        return bill

    def list_bills(self) -> list[BillRecord]:
        """从本地 JSON 账本中读取全部账单。"""
        data = self._read_data()
        return [BillRecord.from_dict(item) for item in data["bills"]]

    def _ensure_file(self) -> None:
        """在账本文件不存在时先创建它。"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write_data({"bills": []})

    def _read_data(self) -> dict[str, list[dict[str, object]]]:
        """从磁盘读取原始 JSON 账本数据。"""
        self._ensure_file()
        with self._path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _write_data(self, data: dict[str, list[dict[str, object]]]) -> None:
        """将原始 JSON 账本数据写回磁盘。"""
        with self._path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
