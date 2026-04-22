from __future__ import annotations

import unittest

from account_agent.service.stat_query_service import StatQueryService


class StubServerClient:
    """用于模拟统计相关后端接口返回值的桩客户端。"""

    def __init__(self) -> None:
        """初始化桩客户端及调用记录。"""
        self.calls: list[dict[str, object]] = []

    def get(self, path: str, *, params=None, headers=None):
        """根据不同路径返回固定测试数据。"""
        self.calls.append({"path": path, "params": params, "headers": headers})
        if path == "/category/list":
            if params == {"type": 1}:
                return [
                    {"id": 1, "name": "工资", "type": 1},
                    {"id": 4, "name": "其他收入", "type": 1},
                ]
            if params == {"type": 2}:
                return [
                    {"id": 5, "name": "餐饮", "type": 2},
                    {"id": 6, "name": "交通", "type": 2},
                    {"id": 12, "name": "其他支出", "type": 2},
                ]
            if params is None:
                return [
                    {"id": 1, "name": "工资", "type": 1},
                    {"id": 5, "name": "餐饮", "type": 2},
                    {"id": 6, "name": "交通", "type": 2},
                    {"id": 12, "name": "其他支出", "type": 2},
                ]
        if path == "/stat/overview":
            return {
                "totalIncome": 2000,
                "totalExpense": 86.5,
                "balance": 1913.5,
                "billCount": 3,
            }
        if path == "/stat/category":
            if params["type"] == 1:
                return [
                    {"categoryName": "工资", "amount": 2000, "proportion": 100},
                ]
            return [
                {"categoryName": "餐饮", "amount": 36.5, "proportion": 42.2},
                {"categoryName": "交通", "amount": 50, "proportion": 57.8},
            ]
        if path == "/bill/list":
            bill_type = params.get("type")
            category_id = params.get("categoryId")
            if bill_type == 2 and category_id == 5:
                return {"total": 1, "list": []}
            if bill_type == 2 and category_id == 6:
                return {"total": 1, "list": []}
            if bill_type == 1:
                return {"total": 1, "list": []}
            if bill_type == 2:
                return {"total": 2, "list": []}
            return {"total": 3, "list": []}
        raise AssertionError(f"Unexpected path: {path}")


class StatQueryServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        """创建待测统计服务与桩客户端。"""
        self.client = StubServerClient()
        self.service = StatQueryService(client=self.client)

    def test_summarize_bills_without_filters(self) -> None:
        """无筛选条件时应组合总览和分类统计结果。"""
        result = self.service.summarize_bills()

        self.assertEqual(
            result,
            {
                "count": 3,
                "total_amount": 2086.5,
                "kind": None,
                "category": None,
                "by_kind": {"income": 2000.0, "expense": 86.5},
                "by_category": {"交通": 50.0, "工资": 2000.0, "餐饮": 36.5},
            },
        )

    def test_summarize_bills_with_kind_and_category(self) -> None:
        """带 kind/category 条件时应只统计对应分类和类型。"""
        result = self.service.summarize_bills({"kind": "expense", "category": "餐饮"})

        self.assertEqual(
            result,
            {
                "count": 1,
                "total_amount": 36.5,
                "kind": "expense",
                "category": "餐饮",
                "by_kind": {"expense": 36.5},
                "by_category": {"餐饮": 36.5},
            },
        )

    def test_summarize_bills_formats_time_filters_for_server(self) -> None:
        """统计接口的时间筛选应统一转换成后端约定格式。"""
        self.service.summarize_bills(
            {
                "startTime": "2026-03-01T00:00:00",
                "endTime": "2026-03-31T23:59:59",
            }
        )

        overview_call = next(call for call in self.client.calls if call["path"] == "/stat/overview")
        self.assertEqual(
            overview_call["params"],
            {
                "startTime": "2026-03-01 00:00:00",
                "endTime": "2026-03-31 23:59:59",
            },
        )
