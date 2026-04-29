from __future__ import annotations

import unittest
from unittest.mock import patch

from account_agent.tools.budget_tools import get_budget_progress, list_budgets, save_budget


class StubBudgetCommandService:
    """用于验证预算写工具是否切到后端服务的桩对象。"""

    def __init__(self) -> None:
        """初始化调用记录。"""
        self.last_payload: dict[str, object] | None = None

    def save_budget(self, payload: dict[str, object]) -> dict[str, object]:
        """记录传入参数并返回模拟后端结果。"""
        self.last_payload = payload
        return {"id": 321}


class StubBudgetQueryService:
    """用于验证预算查询工具是否切到后端服务的桩对象。"""

    def __init__(self) -> None:
        """初始化调用记录。"""
        self.last_list_params: dict[str, object] | None = None
        self.last_progress_params: dict[str, object] | None = None

    def list_budgets(self, params: dict[str, object]) -> list[dict[str, object]]:
        """记录预算列表查询参数并返回模拟结果。"""
        self.last_list_params = params
        return [
            {
                "id": 1,
                "category_id": 11,
                "category": "餐饮",
                "budget_cycle": 1,
                "budget_amount": 800.0,
                "used_amount": 120.0,
                "remain_amount": 680.0,
                "progress": 15.0,
            },
            {
                "id": 2,
                "category_id": 12,
                "category": "交通",
                "budget_cycle": 1,
                "budget_amount": 300.0,
                "used_amount": 80.0,
                "remain_amount": 220.0,
                "progress": 26.67,
            },
        ]

    def get_budget_progress(self, params: dict[str, object]) -> dict[str, object]:
        """记录预算进度查询参数并返回模拟结果。"""
        self.last_progress_params = params
        return {
            "total_budget": 1100.0,
            "total_used": 200.0,
            "total_remain": 900.0,
            "overspend_count": 0,
            "category_progress": [
                {
                    "id": 1,
                    "category_id": 11,
                    "category": "餐饮",
                    "budget_cycle": 1,
                    "budget_amount": 800.0,
                    "used_amount": 120.0,
                    "remain_amount": 680.0,
                    "progress": 15.0,
                }
            ],
        }


class BudgetToolsTestCase(unittest.TestCase):
    def test_save_budget_uses_server_service(self) -> None:
        """保存预算工具应调用后端预算写服务。"""
        command_service = StubBudgetCommandService()
        with patch(
            "account_agent.tools.budget_tools.get_budget_command_service",
            return_value=command_service,
        ):
            result = save_budget.invoke(
                {
                    "category": "餐饮",
                    "budget_cycle": 1,
                    "budget_amount": 800,
                }
            )

        self.assertEqual(
            command_service.last_payload,
            {
                "category": "餐饮",
                "budgetCycle": 1,
                "budgetAmount": 800,
            },
        )
        self.assertEqual(result["budget"]["id"], "321")
        self.assertEqual(result["budget"]["category"], "餐饮")
        self.assertEqual(result["budget"]["budget_cycle"], 1)
        self.assertEqual(result["budget"]["budget_amount"], 800.0)

    def test_save_budget_forwards_authorization_from_config(self) -> None:
        """保存预算工具应从 RunnableConfig 中读取显式鉴权信息。"""
        command_service = StubBudgetCommandService()
        with patch(
            "account_agent.tools.budget_tools.get_budget_command_service",
            return_value=command_service,
        ) as mocked_get_service:
            save_budget.invoke(
                {
                    "category": "餐饮",
                    "budget_cycle": 1,
                    "budget_amount": 800,
                },
                config={
                    "configurable": {
                        "authorization": "Bearer budget-auth-token",
                    }
                },
            )

        mocked_get_service.assert_called_once_with(
            authorization="Bearer budget-auth-token",
            token=None,
        )

    def test_budget_query_tools_use_server_services(self) -> None:
        """预算查询工具应调用对应后端服务。"""
        query_service = StubBudgetQueryService()
        with patch(
            "account_agent.tools.budget_tools.get_budget_query_service",
            return_value=query_service,
        ):
            list_result = list_budgets.invoke({"cycle": 1})
            progress_result = get_budget_progress.invoke({"cycle": 1})

        self.assertEqual(query_service.last_list_params, {"cycle": 1})
        self.assertEqual(query_service.last_progress_params, {"cycle": 1})
        self.assertEqual(list_result["count"], 2)
        self.assertEqual(list_result["items"][0]["category"], "餐饮")
        self.assertEqual(progress_result["progress"]["total_budget"], 1100.0)
        self.assertEqual(progress_result["progress"]["category_progress"][0]["category"], "餐饮")
