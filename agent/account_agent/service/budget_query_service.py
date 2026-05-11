from __future__ import annotations

from typing import Any

from account_agent.api.errors import AgentError
from account_agent.server import ServerClient
from account_agent.service.budget_utils import resolve_budget_cycle


class BudgetQueryService:
    """封装预算读操作，并将后端响应映射为 Agent 使用的结构。"""

    def __init__(self, client: ServerClient | None = None) -> None:
        """创建预算查询服务。"""
        self._client = client or ServerClient()

    def list_budgets(self, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """查询预算列表。"""
        request_params = self._build_cycle_params(params or {}, required=False)
        data = self._client.get("/budget/list", params=request_params)
        if not isinstance(data, list):
            raise AgentError(status_code=500, message="预算列表接口返回格式不正确")
        return [self._map_budget_item(item) for item in data]

    def get_budget_progress(self, params: dict[str, Any]) -> dict[str, Any]:
        """查询整体预算进度。"""
        request_params = self._build_cycle_params(params or {}, required=True)
        data = self._client.get("/budget/progress", params=request_params)
        if not isinstance(data, dict):
            raise AgentError(status_code=500, message="预算进度接口返回格式不正确")

        category_progress = data.get("categoryProgress", [])
        if not isinstance(category_progress, list):
            raise AgentError(status_code=500, message="categoryProgress 字段格式不正确")

        return {
            "total_budget": self._to_float(data.get("totalBudget")),
            "total_used": self._to_float(data.get("totalUsed")),
            "total_remain": self._to_float(data.get("totalRemain")),
            "overspend_count": int(data.get("overspendCount", 0)),
            "category_progress": [self._map_budget_item(item) for item in category_progress],
        }

    def _build_cycle_params(self, params: dict[str, Any], *, required: bool) -> dict[str, Any]:
        """构造预算周期查询参数。"""
        raw_cycle = params.get("cycle", params.get("budgetCycle"))
        cycle = resolve_budget_cycle(raw_cycle, field_name="cycle", required=required)
        return {"cycle": cycle} if cycle is not None else {}

    def _map_budget_item(self, item: Any) -> dict[str, Any]:
        """将预算列表项映射为 Agent 使用的统一结构。"""
        if not isinstance(item, dict):
            raise AgentError(status_code=500, message="预算列表项格式不正确")

        return {
            "id": int(item.get("id", 0)),
            "category_id": int(item.get("categoryId", 0)),
            "category": str(item.get("categoryName", "")),
            "budget_cycle": int(item.get("budgetCycle", 0)),
            "budget_amount": self._to_float(item.get("budgetAmount")),
            "used_amount": self._to_float(item.get("usedAmount")),
            "remain_amount": self._to_float(item.get("remainAmount")),
            "progress": self._to_float(item.get("progress")),
        }

    @staticmethod
    def _to_float(value: Any) -> float:
        """将后端金额字段统一转成两位小数浮点数。"""
        if value in (None, ""):
            return 0.0
        try:
            return round(float(value), 2)
        except (TypeError, ValueError) as exc:
            raise AgentError(status_code=500, message="预算金额字段格式不正确") from exc
