from __future__ import annotations

from typing import Any

from account_agent.api.errors import AgentError
from account_agent.server import ServerClient
from account_agent.service.category_service import CategoryService


class BudgetCommandService:
    """封装预算写操作，并负责将 Agent 字段映射到后端请求结构。"""

    def __init__(self, client: ServerClient | None = None) -> None:
        """创建预算写操作服务。"""
        self._client = client or ServerClient()
        self._category_service = CategoryService(client=self._client)

    def save_budget(self, payload: dict[str, Any]) -> dict[str, Any]:
        """保存或修改预算。"""
        request_body = {
            "categoryId": self._resolve_category_id(payload),
            "budgetCycle": self._resolve_budget_cycle(payload),
            "budgetAmount": self._resolve_budget_amount(payload),
        }
        data = self._client.post("/budget", json_body=request_body)
        if not isinstance(data, dict):
            raise AgentError(status_code=500, message="预算保存接口返回格式不正确")
        return data

    def _resolve_category_id(self, payload: dict[str, Any]) -> int:
        """优先使用 categoryId，否则根据分类名称解析系统分类 ID。"""
        category_id = payload.get("categoryId")
        if category_id is not None:
            try:
                return int(category_id)
            except (TypeError, ValueError) as exc:
                raise AgentError(status_code=400, message="categoryId must be a number") from exc

        category_name = str(payload.get("category", "")).strip()
        if not category_name:
            raise AgentError(status_code=400, message="category or categoryId is required")

        # 预算默认是支出分类
        return self._category_service.resolve_category_id(category_name=category_name, bill_type=2)

    def _resolve_budget_cycle(self, payload: dict[str, Any]) -> int:
        """将预算周期转换为后端枚举值。"""
        raw_cycle = payload.get("budgetCycle", payload.get("budget_cycle"))
        if raw_cycle is None:
            raise AgentError(status_code=400, message="budgetCycle is required")

        if isinstance(raw_cycle, str):
            text = raw_cycle.strip()
            cycle_aliases = {
                "月": 1,
                "月度": 1,
                "monthly": 1,
                "季度": 2,
                "季": 2,
                "quarter": 2,
                "quarterly": 2,
                "年度": 3,
                "年": 3,
                "year": 3,
                "yearly": 3,
                "annual": 3,
            }
            if text in cycle_aliases:
                return cycle_aliases[text]
            try:
                raw_cycle = int(text)
            except ValueError as exc:
                raise AgentError(status_code=400, message="budgetCycle must be 1, 2 or 3") from exc

        try:
            cycle = int(raw_cycle)
        except (TypeError, ValueError) as exc:
            raise AgentError(status_code=400, message="budgetCycle must be a number") from exc

        if cycle not in {1, 2, 3}:
            raise AgentError(status_code=400, message="budgetCycle must be 1, 2 or 3")
        return cycle

    def _resolve_budget_amount(self, payload: dict[str, Any]) -> float:
        """校验预算金额并统一保留两位小数。"""
        raw_amount = payload.get("budgetAmount", payload.get("budget_amount"))
        if raw_amount is None:
            raise AgentError(status_code=400, message="budgetAmount is required")
        try:
            amount = round(float(raw_amount), 2)
        except (TypeError, ValueError) as exc:
            raise AgentError(status_code=400, message="budgetAmount must be a number") from exc
        if amount <= 0:
            raise AgentError(status_code=400, message="budgetAmount must be greater than 0")
        return amount
