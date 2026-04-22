from __future__ import annotations

import unittest

from account_agent.api.errors import AgentError
from account_agent.service.bill_command_service import BillCommandService


class StubServerClient:
    """用于验证服务端入参与返回值的简单桩客户端。"""

    def __init__(self) -> None:
        """初始化桩客户端内部状态。"""
        self.last_post: dict[str, object] | None = None
        self.last_get: dict[str, object] | None = None

    def get(self, path: str, *, params=None, headers=None):
        """返回固定分类列表，供分类 ID 解析使用。"""
        self.last_get = {"path": path, "params": params, "headers": headers}
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
        raise AssertionError(f"Unexpected GET path: {path}")

    def post(self, path: str, *, json_body=None, headers=None):
        """记录调用参数并返回固定成功结果。"""
        self.last_post = {
            "path": path,
            "json_body": json_body,
            "headers": headers,
        }
        return {"id": 101, "overspendAlert": None}


class BillCommandServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        """创建待测服务与桩客户端。"""
        self.client = StubServerClient()
        self.service = BillCommandService(client=self.client)

    def test_add_bill_maps_agent_payload_to_server_request(self) -> None:
        """Agent 风格字段应被正确映射成后端新增账单入参。"""
        result = self.service.add_bill(
            {
                "amount": 8.71,
                "kind": "expense",
                "category": "交通",
                "note": "打车回家",
                "occurred_at": "2026-04-21T19:25:30",
            }
        )

        self.assertEqual(result["id"], 101)
        self.assertEqual(self.client.last_post["path"], "/bill")
        self.assertEqual(
            self.client.last_post["json_body"],
            {
                "categoryId": 6,
                "amount": 8.71,
                "type": 2,
                "remark": "打车回家",
                "recordTime": "2026-04-21 19:25:30",
                "isAiGenerated": 0,
            },
        )

    def test_add_bill_supports_server_style_payload(self) -> None:
        """已经是后端字段风格的入参应直接兼容。"""
        self.service.add_bill(
            {
                "categoryId": 1,
                "amount": 2000,
                "type": 1,
                "remark": "四月工资",
                "recordTime": "2026-04-21 09:00:00",
                "isAiGenerated": 0,
            }
        )

        self.assertEqual(
            self.client.last_post["json_body"],
            {
                "categoryId": 1,
                "amount": 2000.0,
                "type": 1,
                "remark": "四月工资",
                "recordTime": "2026-04-21 09:00:00",
                "isAiGenerated": 0,
            },
        )

    def test_add_bill_maps_other_category_by_kind(self) -> None:
        """其他分类应根据收入或支出映射到对应系统分类。"""
        self.service.add_bill(
            {
                "amount": 50,
                "kind": "income",
                "category": "其他",
            }
        )

        self.assertEqual(self.client.last_post["json_body"]["categoryId"], 4)

    def test_add_bill_rejects_unknown_category(self) -> None:
        """无法映射的分类应返回明确的参数错误。"""
        with self.assertRaises(AgentError) as context:
            self.service.add_bill(
                {
                    "amount": 50,
                    "kind": "expense",
                    "category": "火锅",
                }
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("unsupported category", context.exception.message)
