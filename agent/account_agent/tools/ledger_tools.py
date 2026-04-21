from __future__ import annotations

from functools import lru_cache

from langchain_core.tools import tool

from account_agent.config import get_settings
from account_agent.service.ledger_service import LedgerService
from account_agent.storage import JsonLedgerStore


@lru_cache(maxsize=1)
def get_ledger_service() -> LedgerService:
    """创建并缓存工具层复用的账本服务。"""
    settings = get_settings()
    return LedgerService(JsonLedgerStore(settings.ledger_path))


@tool
def add_bill(
    amount: float,
    kind: str,
    category: str,
    note: str = "",
    occurred_at: str | None = None,
) -> dict[str, object]:
    """新增一笔账单，金额必须为正，kind 只能是 expense 或 income。"""
    bill = get_ledger_service().add_bill(
        amount=amount,
        kind=kind,
        category=category,
        note=note,
        occurred_at=occurred_at,
    )
    return {"ok": True, "bill": bill}


@tool
def list_recent_bills(
    limit: int = 5,
    kind: str | None = None,
    category: str | None = None,
) -> dict[str, object]:
    """查询最近账单，可按 kind 或 category 过滤。"""
    bills = get_ledger_service().list_recent_bills(
        limit=limit,
        kind=kind,
        category=category,
    )
    return {"ok": True, "count": len(bills), "items": bills}


@tool
def summarize_bills(
    kind: str | None = None,
    category: str | None = None,
) -> dict[str, object]:
    """按收支类型和分类汇总账单。"""
    summary = get_ledger_service().summarize_bills(kind=kind, category=category)
    return {"ok": True, "summary": summary}


def get_ledger_tools() -> list:
    """返回账本工具集合。"""
    return [add_bill, list_recent_bills, summarize_bills]


def get_tools() -> list:
    """返回图默认暴露的工具集合。"""
    return get_ledger_tools()
