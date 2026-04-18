from __future__ import annotations

from functools import lru_cache

from langchain_core.tools import tool

from account_agent.config import get_settings
from account_agent.service.ledger_service import LedgerService
from account_agent.storage import SqliteLedgerStore


@lru_cache(maxsize=1)
def get_ledger_service() -> LedgerService:
    settings = get_settings()
    return LedgerService(SqliteLedgerStore(settings.ledger_db_path))


@tool
def add_bill(
    amount: float,
    kind: str,
    category: str,
    note: str = "",
    occurred_at: str | None = None,
) -> dict[str, object]:
    """Add a bill. Use a positive amount. `kind` must be `expense` or `income`."""
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
    """List recent bills, optionally filtered by `kind` or `category`."""
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
    """Summarize bills by income or expense kind and category."""
    summary = get_ledger_service().summarize_bills(kind=kind, category=category)
    return {"ok": True, "summary": summary}


def get_tools() -> list:
    return [add_bill, list_recent_bills, summarize_bills]
