from __future__ import annotations

import unittest

from account_agent.api.errors import AgentError
from account_agent.service.bill_query_service import BillQueryService


class StubServerClient:
    """用于验证查询参数和响应映射的简单桩客户端。"""

    def __init__(self) -> None:
        """初始化桩客户端内部状态。"""
        self.last_get: dict[str, object] | None = None

    def get(self, path: str, *, params=None, headers=None):
        """记录 GET 调用参数，并返回固定账单列表数据。"""
        self.last_get = {
            "path": path,
            "params": params,
            "headers": headers,
        }
        if path == "/category/list":
            if params == {"type": 2}:
                return [
                    {"id": 5, "name": "餐饮", "type": 2},
                    {"id": 12, "name": "其他支出", "type": 2},
                ]
            if params is None:
                return [
                    {"id": 1, "name": "工资", "type": 1},
                    {"id": 5, "name": "餐饮", "type": 2},
                    {"id": 12, "name": "其他支出", "type": 2},
                ]
        return {
            "total": 2,
            "list": [
                {
                    "id": 101,
                    "amount": 36.5,
                    "type": 2,
                    "categoryName": "餐饮",
                    "remark": "午饭",
                    "recordTime": "2026-03-27 12:30:00",
                    "isAiGenerated": 0,
                }
            ],
        }


class BillQueryServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        """创建待测服务与桩客户端。"""
        self.client = StubServerClient()
        self.service = BillQueryService(client=self.client)

    def test_list_recent_bills_maps_agent_filters(self) -> None:
        """Agent 风格筛选条件应正确转换成后端查询参数。"""
        result = self.service.list_recent_bills(
            {
                "limit": 3,
                "kind": "expense",
                "category": "餐饮",
                "startTime": "2026-03-01T00:00:00",
                "endTime": "2026-03-31 23:59:59",
            }
        )

        self.assertEqual(self.client.last_get["path"], "/bill/list")
        self.assertEqual(
            self.client.last_get["params"],
            {
                "pageNum": 1,
                "pageSize": 3,
                "startTime": "2026-03-01 00:00:00",
                "endTime": "2026-03-31 23:59:59",
                "type": 2,
                "categoryId": 5,
            },
        )
        self.assertEqual(
            result,
            [
                {
                    "id": "101",
                    "amount": 36.5,
                    "kind": "expense",
                    "category": "餐饮",
                    "note": "午饭",
                    "occurred_at": "2026-03-27T12:30:00",
                    "created_at": "2026-03-27T12:30:00",
                    "is_ai_generated": 0,
                }
            ],
        )

    def test_list_recent_bills_supports_server_style_filters(self) -> None:
        """后端原生筛选字段也应直接兼容。"""
        self.service.list_recent_bills(
            {
                "pageNum": 2,
                "pageSize": 10,
                "type": 1,
                "categoryId": 1,
            }
        )

        self.assertEqual(
            self.client.last_get["params"],
            {
                "pageNum": 2,
                "pageSize": 10,
                "type": 1,
                "categoryId": 1,
            },
        )

    def test_list_recent_bills_requires_kind_for_other_category(self) -> None:
        """category 为其他但未传 kind/type 时应明确报错。"""
        with self.assertRaisesRegex(AgentError, "kind or type is required"):
            self.service.list_recent_bills({"category": "其他"})
