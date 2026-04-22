from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from account_agent.storage import BillRecord


VALID_KINDS = {"expense", "income"}
CANONICAL_CATEGORIES = ("餐饮", "交通", "购物", "工资", "住房", "其他")
CATEGORY_ALIASES = {
    "food": "餐饮",
    "meal": "餐饮",
    "dining": "餐饮",
    "lunch": "餐饮",
    "dinner": "餐饮",
    "taxi": "交通",
    "bus": "交通",
    "subway": "交通",
    "transport": "交通",
    "shopping": "购物",
    "shop": "购物",
    "salary": "工资",
    "payroll": "工资",
    "rent": "住房",
    "housing": "住房",
}


class LedgerStore(Protocol):
    def append_bill(self, bill: BillRecord) -> BillRecord:
        """持久化一条账单记录。"""
        ...

    def list_bills(self) -> list[BillRecord]:
        """返回所有已持久化的账单记录。"""
        ...


class LedgerService:
    def __init__(self, store: LedgerStore) -> None:
        """基于给定存储实现创建账本服务。"""
        self._store = store

    def     add_bill(
        self,
        *,
        amount: float,
        kind: str,
        category: str,
        note: str = "",
        occurred_at: str | None = None,
    ) -> dict[str, object]:
        """校验并保存一条账单记录。"""
        normalized_kind = self._normalize_kind(kind)
        normalized_category = self._normalize_category(category)
        normalized_amount = self._normalize_amount(amount)
        occurred_time = self._normalize_datetime(occurred_at)
        created_time = datetime.now().isoformat(timespec="seconds")

        bill = BillRecord(
            id=uuid4().hex,
            amount=normalized_amount,
            kind=normalized_kind,
            category=normalized_category,
            note=note.strip(),
            occurred_at=occurred_time,
            created_at=created_time,
        )
        self._store.append_bill(bill)
        return bill.to_dict()

    def list_recent_bills(
        self,
        *,
        limit: int = 5,
        kind: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, object]]:
        """按可选条件返回最近的账单列表。"""
        records = self._filter_bills(kind=kind, category=category)
        records.sort(key=lambda item: (item.occurred_at, item.created_at), reverse=True)
        safe_limit = max(1, limit)
        return [record.to_dict() for record in records[:safe_limit]]

    def summarize_bills(
        self,
        *,
        kind: str | None = None,
        category: str | None = None,
    ) -> dict[str, object]:
        """按收支类型和分类汇总账单金额。"""
        records = self._filter_bills(kind=kind, category=category)
        by_kind: Counter[str] = Counter()
        by_category: defaultdict[str, float] = defaultdict(float)

        for record in records:
            by_kind[record.kind] += record.amount
            by_category[record.category] += record.amount

        total_amount = round(sum(record.amount for record in records), 2)
        return {
            "count": len(records),
            "total_amount": total_amount,
            "kind": self._normalize_kind(kind) if kind else None,
            "category": self._normalize_category(category) if category else None,
            "by_kind": {name: round(value, 2) for name, value in by_kind.items()},
            "by_category": {
                name: round(value, 2) for name, value in sorted(by_category.items())
            },
        }

    def _filter_bills(
        self,
        *,
        kind: str | None = None,
        category: str | None = None,
    ) -> list[BillRecord]:
        """按收支类型和分类过滤已存储账单。"""
        records = self._store.list_bills()
        normalized_kind = self._normalize_kind(kind) if kind else None
        normalized_category = self._normalize_category(category) if category else None

        return [
            record
            for record in records
            if (normalized_kind is None or record.kind == normalized_kind)
            and (normalized_category is None or record.category == normalized_category)
        ]

    @staticmethod
    def _normalize_amount(amount: float) -> float:
        """规范化并校验输入金额。"""
        normalized_amount = round(float(amount), 2)
        if normalized_amount <= 0:
            raise ValueError("amount must be a positive number")
        return normalized_amount

    @staticmethod
    def _normalize_kind(kind: str | None) -> str:
        """规范化并校验收入或支出类型。"""
        if kind is None:
            raise ValueError("kind is required")
        normalized_kind = kind.strip().lower()
        if normalized_kind not in VALID_KINDS:
            raise ValueError("kind must be `expense` or `income`")
        return normalized_kind

    @staticmethod
    def _normalize_category(category: str | None) -> str:
        """将分类规范化为支持的标准集合。"""
        if not category:
            return "其他"

        stripped = category.strip()
        if stripped in CANONICAL_CATEGORIES:
            return stripped

        alias = CATEGORY_ALIASES.get(stripped.lower())
        if alias:
            return alias

        return "其他"

    @staticmethod
    def _normalize_datetime(occurred_at: str | None) -> str:
        """将发生时间规范化为秒级 ISO 格式。"""
        if not occurred_at:
            return datetime.now().isoformat(timespec="seconds")
        return datetime.fromisoformat(occurred_at.strip()).isoformat(timespec="seconds")
