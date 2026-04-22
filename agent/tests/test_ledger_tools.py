from __future__ import annotations

import unittest
from unittest.mock import patch

from account_agent.tools.ledger_tools import add_bill, list_recent_bills, summarize_bills


class StubBillCommandService:
    """用于验证新增账单工具是否切到后端服务的桩对象。"""

    def __init__(self) -> None:
        """初始化调用记录。"""
        self.last_payload: dict[str, object] | None = None

    def add_bill(self, payload: dict[str, object]) -> dict[str, object]:
        """记录传入参数并返回模拟后端结果。"""
        self.last_payload = payload
        return {"id": 123, "overspendAlert": "本月餐饮预算已接近上限"}


class StubBillQueryService:
    """用于验证账单查询工具是否切到后端服务的桩对象。"""

    def __init__(self) -> None:
        """初始化调用记录。"""
        self.last_params: dict[str, object] | None = None

    def list_recent_bills(self, params: dict[str, object]) -> list[dict[str, object]]:
        """记录查询参数并返回模拟账单列表。"""
        self.last_params = params
        return [{"id": "1", "amount": 12.5, "kind": "expense", "category": "餐饮"}]


class StubStatQueryService:
    """用于验证统计工具是否切到后端服务的桩对象。"""

    def __init__(self) -> None:
        """初始化调用记录。"""
        self.last_params: dict[str, object] | None = None

    def summarize_bills(self, params: dict[str, object]) -> dict[str, object]:
        """记录统计参数并返回模拟汇总结果。"""
        self.last_params = params
        return {"count": 1, "total_amount": 12.5, "by_kind": {"expense": 12.5}, "by_category": {"餐饮": 12.5}}


class LedgerToolsTestCase(unittest.TestCase):
    def test_add_bill_uses_server_service(self) -> None:
        """新增工具应调用后端账单服务。"""
        command_service = StubBillCommandService()
        with patch("account_agent.tools.ledger_tools.get_bill_command_service",
            return_value=command_service,
        ):
            result = add_bill.invoke(
                {
                    "amount": 18.8,
                    "kind": "expense",
                    "category": "餐饮",
                    "note": "晚饭",
                    "occurred_at": "2026-04-22T19:00:00",
                }
            )

        self.assertEqual(command_service.last_payload["isAiGenerated"], 1)
        self.assertEqual(result["bill"]["id"], "123")
        self.assertEqual(result["overspendAlert"], "本月餐饮预算已接近上限")

    def test_add_bill_forwards_authorization_from_config(self) -> None:
        """新增工具应从 RunnableConfig 中读取显式鉴权信息。"""
        command_service = StubBillCommandService()
        with patch(
            "account_agent.tools.ledger_tools.get_bill_command_service",
            return_value=command_service,
        ) as mocked_get_service:
            add_bill.invoke(
                {
                    "amount": 18.8,
                    "kind": "expense",
                    "category": "餐饮",
                    "note": "晚饭",
                    "occurred_at": "2026-04-22T19:00:00",
                },
                config={
                    "configurable": {
                        "authorization": "Bearer tool-auth-token",
                    }
                },
            )

        mocked_get_service.assert_called_once_with(
            authorization="Bearer tool-auth-token",
            token=None,
        )

    def test_query_tools_use_server_services(self) -> None:
        """查询和统计工具应调用对应后端服务。"""
        bill_query_service = StubBillQueryService()
        stat_query_service = StubStatQueryService()
        with patch("account_agent.tools.ledger_tools.get_bill_query_service",
            return_value=bill_query_service,
        ), patch(
            "account_agent.tools.ledger_tools.get_stat_query_service",
            return_value=stat_query_service,
        ):
            list_result = list_recent_bills.invoke({"limit": 3, "kind": "expense", "category": "餐饮"})
            stat_result = summarize_bills.invoke({"kind": "expense", "category": "餐饮"})

        self.assertEqual(bill_query_service.last_params, {"limit": 3, "kind": "expense", "category": "餐饮"})
        self.assertEqual(stat_query_service.last_params, {"kind": "expense", "category": "餐饮"})
        self.assertEqual(list_result["count"], 1)
        self.assertEqual(stat_result["summary"]["total_amount"], 12.5)
