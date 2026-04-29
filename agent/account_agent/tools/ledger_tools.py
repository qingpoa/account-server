from __future__ import annotations

from datetime import datetime
from functools import lru_cache

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from account_agent.server import ServerClient
from account_agent.service.bill_command_service import BillCommandService
from account_agent.service.bill_query_service import BillQueryService
from account_agent.service.stat_query_service import StatQueryService


def _resolve_request_auth(config: RunnableConfig | None) -> tuple[str | None, str | None]:
    """从 LangGraph configurable 中读取当前请求的鉴权信息。"""
    configurable = (config or {}).get("configurable", {})
    if not isinstance(configurable, dict):
        return None, None
    authorization = configurable.get("authorization")
    token = configurable.get("token")
    return (
        str(authorization).strip() if authorization else None,
        str(token).strip() if token else None,
    )


@lru_cache(maxsize=128)
def get_bill_command_service(
    authorization: str | None = None,
    token: str | None = None,
) -> BillCommandService:
    """创建并缓存后端新增账单服务。"""
    return BillCommandService(
        client=ServerClient(authorization=authorization, token=token),
    )


@lru_cache(maxsize=128)
def get_bill_query_service(
    authorization: str | None = None,
    token: str | None = None,
) -> BillQueryService:
    """创建并缓存后端账单查询服务。"""
    return BillQueryService(
        client=ServerClient(authorization=authorization, token=token),
    )


@lru_cache(maxsize=128)
def get_stat_query_service(
    authorization: str | None = None,
    token: str | None = None,
) -> StatQueryService:
    """创建并缓存后端统计查询服务。"""
    return StatQueryService(
        client=ServerClient(authorization=authorization, token=token),
    )


def _build_tool_bill_payload(
    *,
    server_result: dict[str, object],
    amount: float,
    kind: str,
    category: str,
    note: str,
    occurred_at: str | None,
) -> dict[str, object]:
    """将后端新增账单结果补齐为图内统一使用的 bill 结构。"""
    normalized_kind = kind.strip().lower()
    normalized_category = category.strip() or "其他"
    normalized_note = note.strip()
    occurred_time = occurred_at or datetime.now().isoformat(timespec="seconds")
    created_time = datetime.now().isoformat(timespec="seconds")
    return {
        "id": str(server_result.get("id", "")),
        "amount": round(float(amount), 2),
        "kind": normalized_kind,
        "category": normalized_category,
        "note": normalized_note,
        "occurred_at": occurred_time,
        "created_at": created_time,
    }


@tool
def add_bill(
    amount: float,
    kind: str,
    category: str,
    note: str = "",
    occurred_at: str | None = None,
    config: RunnableConfig = None,
) -> dict[str, object]:
    """新增一笔账单，金额必须为正，kind 只能是 expense 或 income。"""
    authorization, token = _resolve_request_auth(config)
    result = get_bill_command_service(authorization=authorization, token=token).add_bill(
        {
            "amount": amount,
            "kind": kind,
            "category": category,
            "note": note,
            "occurred_at": occurred_at,
            "isAiGenerated": 1,
        }
    )
    return {
        "ok": True,
        "bill": _build_tool_bill_payload(
            server_result=result,
            amount=amount,
            kind=kind,
            category=category,
            note=note,
            occurred_at=occurred_at,
        ),
        "overspendAlert": result.get("overspendAlert") if isinstance(result, dict) else None,
    }


@tool
def list_recent_bills(
    limit: int = 5,
    kind: str | None = None,
    category: str | None = None,
    config: RunnableConfig = None,
) -> dict[str, object]:
    """查询最近账单，可按 kind 或 category 过滤。"""
    authorization, token = _resolve_request_auth(config)
    bills = get_bill_query_service(authorization=authorization, token=token).list_recent_bills(
        {
            "limit": limit,
            "kind": kind,
            "category": category,
        }
    )
    return {"ok": True, "count": len(bills), "items": bills}


@tool
def summarize_bills(
    kind: str | None = None,
    category: str | None = None,
    config: RunnableConfig = None,
) -> dict[str, object]:
    """按收支类型和分类汇总账单。"""
    authorization, token = _resolve_request_auth(config)
    summary = get_stat_query_service(authorization=authorization, token=token).summarize_bills(
        {
            "kind": kind,
            "category": category,
        }
    )
    return {"ok": True, "summary": summary}


def get_ledger_tools() -> list:
    """返回账本工具集合。"""
    return [add_bill, list_recent_bills, summarize_bills]
