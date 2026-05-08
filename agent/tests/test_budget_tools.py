from __future__ import annotations

import unittest
from unittest.mock import patch

from account_agent.tools.budget_tools import get_budget_progress, list_budgets, save_budget


class StubBudgetCommandService:
    """记录预算写入调用的桩对象。"""

    def __init__(self) -> None:
        self.last_payload: dict[str, object] | None = None

    def save_budget(self, payload: dict[str, object]) -> dict[str, object]:
        self.last_payload = payload
        return {"id": 321}


class StubBudgetQueryService:
    """记录预算查询调用的桩对象。"""

    def __init__(self) -> None:
        self.last_list_params: dict[str, object] | None = None
        self.last_progress_params: dict[str, object] | None = None

    def list_budgets(self, params: dict[str, object]) -> list[dict[str, object]]:
        self.last_list_params = params
        return [
            {"id": 1, "category": "餐饮", "budget_amount": 800.0},
            {"id": 2, "category": "交通", "budget_amount": 300.0},
        ]

    def get_budget_progress(self, params: dict[str, object]) -> dict[str, object]:
        self.last_progress_params = params
        return {
            "total_budget": 1100.0,
            "total_used": 200.0,
            "total_remain": 900.0,
            "overspend_count": 0,
            "category_progress": [{"category": "餐饮", "progress": 15.0}],
        }


class BudgetToolsTestCase(unittest.TestCase):
    def test_save_budget_uses_server_service(self) -> None:
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
