from __future__ import annotations

from functools import lru_cache

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from account_agent.server import ServerClient
from account_agent.service.budget_command_service import BudgetCommandService
from account_agent.service.budget_query_service import BudgetQueryService


class SaveBudgetInput(BaseModel):
    """定义新增或修改预算工具的输入参数。"""

    category: str = Field(
        description="预算分类名称，如餐饮、交通、购物、住房、其他。",
    )
    budget_cycle: int = Field(
        description="预算周期，1 表示月度，2 表示季度，3 表示年度。",
    )
    budget_amount: float = Field(
        description="预算金额，必须是正数，例如 800 或 1500。",
    )


class ListBudgetsInput(BaseModel):
    """定义预算列表查询工具的输入参数。"""

    cycle: int | None = Field(
        default=None,
        description="可选的预算周期过滤条件，1 表示月度，2 表示季度，3 表示年度；不传表示查询全部预算。",
    )


class GetBudgetProgressInput(BaseModel):
    """定义预算进度查询工具的输入参数。"""

    cycle: int = Field(
        description="要查询的预算周期，1 表示月度，2 表示季度，3 表示年度。",
    )


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
def get_budget_command_service(
    authorization: str | None = None,
    token: str | None = None,
) -> BudgetCommandService:
    """创建并缓存后端新增预算服务。"""
    return BudgetCommandService(
        client=ServerClient(authorization=authorization, token=token),
    )

@lru_cache(maxsize=128)
def get_budget_query_service(
    authorization: str | None = None,
    token: str | None = None,
) -> BudgetQueryService:
    """创建并缓存后端预算查询服务。"""
    return BudgetQueryService(
        client=ServerClient(authorization=authorization, token=token),
    )


@tool(args_schema=SaveBudgetInput)
def save_budget(
    category: str,
    budget_cycle: int,
    budget_amount: float,
    config: RunnableConfig = None,
) -> dict[str, object]:
    """保存或修改预算，预算周期只允许 1(月度)、2(季度)、3(年度)。"""
    authorization, token = _resolve_request_auth(config)
    result = get_budget_command_service(authorization=authorization, token=token).save_budget(
        {
            "category": category,
            "budgetCycle": budget_cycle,
            "budgetAmount": budget_amount,
        }
    )
    return {
        "ok": True,
        "budget": {
            "id": str(result.get("id", "")),
            "category": category,
            "budget_cycle": budget_cycle,
            "budget_amount": round(float(budget_amount), 2),
        }
    }


@tool(args_schema=ListBudgetsInput)
def list_budgets(
    cycle: int | None = None,
    config: RunnableConfig = None,
) -> dict[str, object]:
    """查询预算列表，可按预算周期过滤。"""
    authorization, token = _resolve_request_auth(config)
    result = get_budget_query_service(authorization=authorization, token=token).list_budgets(
        {"cycle": cycle}
    )
    return {
        "ok": True,
        "count": len(result),
        "items": result,
    }


@tool(args_schema=GetBudgetProgressInput)
def get_budget_progress(
    cycle: int,
    config: RunnableConfig = None,
) -> dict[str, object]:
    """查询指定预算周期的整体预算进度。"""
    authorization, token = _resolve_request_auth(config)

    progress = get_budget_query_service(
        authorization=authorization,
        token=token,
    ).get_budget_progress(
        {
            "cycle": cycle,
        }
    )
    return {
        "ok": True,
        "progress": progress,
    }


def get_budget_tools() -> list:
    """返回预算工具集合。"""
    return [save_budget, list_budgets, get_budget_progress]
