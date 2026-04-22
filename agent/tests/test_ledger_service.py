from __future__ import annotations

import base64
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from account_agent.config import get_settings
from account_agent.graph import build_graph, create_local_agent
from account_agent.graph.builder import _recent_add_bill_payloads
from account_agent.service.image_analysis_service import ImageAnalysisService
from account_agent.service.ledger_service import LedgerService
from account_agent.storage import JsonLedgerStore
from account_agent.tools.ledger_tools import (
    get_bill_command_service,
    get_bill_query_service,
    get_stat_query_service,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
ROOT_RUNTIME_DIR = Path(__file__).resolve().parents[2] / "tests_runtime"


class ToolFriendlyFakeListChatModel(FakeListChatModel):
    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        """在绑定工具后直接返回假模型自身。"""
        return self


class PendingBillCompletionModel(ToolFriendlyFakeListChatModel):
    def invoke(self, input, config=None, **kwargs):
        """模拟在后续轮次中补全图片账单缺失字段。"""
        if isinstance(input, list):
            messages = input
            has_pending_context = any(
                isinstance(message, SystemMessage)
                and "待补全" in str(message.content)
                and "账单候选" in str(message.content)
                for message in messages
            )
            last_human = next(
                (message for message in reversed(messages) if isinstance(message, HumanMessage)),
                None,
            )
            if has_pending_context and last_human and "金额 36" in str(last_human.content):
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "add_bill",
                            "args": {
                                "amount": 36,
                                "kind": "expense",
                                "category": "交通",
                                "note": "滴滴打车",
                                "occurred_at": "2026-04-19T09:30:00",
                            },
                            "id": "call_pending_fill",
                            "type": "tool_call",
                        }
                    ],
                )
        return super().invoke(input, config=config, **kwargs)


class TextAddBillReplyModel(ToolFriendlyFakeListChatModel):
    def __init__(self) -> None:
        """准备一个先记账后返回回执回复的假模型。"""
        super().__init__(responses=["unused"])
        self._call_count = 0

    def invoke(self, input, config=None, **kwargs):
        """第一次返回工具调用，第二次返回自然语言回执。"""
        self._call_count += 1
        if self._call_count == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "add_bill",
                        "args": {
                            "amount": 2000,
                            "kind": "income",
                            "category": "工资",
                            "note": "工资收入",
                            "occurred_at": "2026-04-20T10:00:00",
                        },
                        "id": "call_text_add_bill",
                        "type": "tool_call",
                    }
                ],
            )
        return AIMessage(
            content="已为你记下一笔收入：2000.0 元，分类工资，时间 2026-04-20 10:00，备注 工资收入。如果需要，我还可以继续帮你查询最近流水或做分类统计。"
        )


class MultiAddBillReplyModel(ToolFriendlyFakeListChatModel):
    def __init__(self) -> None:
        """准备一个一次新增两笔账并返回汇总回执的假模型。"""
        super().__init__(responses=["unused"])
        self._call_count = 0

    def invoke(self, input, config=None, **kwargs):
        """第一次返回两条工具调用，第二次返回多笔汇总回执。"""
        self._call_count += 1
        if self._call_count == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "add_bill",
                        "args": {
                            "amount": 40,
                            "kind": "expense",
                            "category": "餐饮",
                            "note": "吃饭",
                            "occurred_at": "2026-04-22T19:27:34",
                        },
                        "id": "call_multi_add_bill_1",
                        "type": "tool_call",
                    },
                    {
                        "name": "add_bill",
                        "args": {
                            "amount": 22222,
                            "kind": "income",
                            "category": "工资",
                            "note": "工资收入",
                            "occurred_at": "2026-04-22T19:27:34",
                        },
                        "id": "call_multi_add_bill_2",
                        "type": "tool_call",
                    },
                ],
            )
        return AIMessage(
            content=(
                "这次一共为你记下 2 笔账：一笔是 40.0 元的餐饮支出，备注吃饭；"
                "另一笔是 22222.0 元的工资收入，备注工资收入。"
            )
        )


class StubImageAnalysisService:
    def __init__(self, result: dict[str, object]) -> None:
        """保存一份固定图片分析结果供测试复用。"""
        self.result = result
        self.calls: list[dict[str, object]] = []

    def analyze(
        self,
        *,
        image_blocks: list[dict[str, object]],
        user_text: str = "",
    ) -> dict[str, object]:
        """记录分析调用并返回固定结果。"""
        self.calls.append(
            {
                "image_blocks": image_blocks,
                "user_text": user_text,
            }
        )
        return dict(self.result)


class ExplodingImageAnalysisService:
    def analyze(
        self,
        *,
        image_blocks: list[dict[str, object]],
        user_text: str = "",
    ) -> dict[str, object]:
        """一旦意外进入图片分析分支就立即失败。"""
        raise AssertionError("image analysis should not be called for text-only requests")


class LocalBillCommandAdapter:
    """在图测试中用本地账本模拟后端新增账单服务。"""

    def __init__(self, service: LedgerService) -> None:
        """保存本地账本服务引用。"""
        self._service = service

    def add_bill(self, payload: dict[str, object]) -> dict[str, object]:
        """将后端风格调用转发到本地账本服务。"""
        bill = self._service.add_bill(
            amount=float(payload["amount"]),
            kind=str(payload["kind"]),
            category=str(payload["category"]),
            note=str(payload.get("note", "")),
            occurred_at=str(payload["occurred_at"]) if payload.get("occurred_at") else None,
        )
        return {"id": bill["id"], "overspendAlert": None}


class LocalBillQueryAdapter:
    """在图测试中用本地账本模拟后端账单查询服务。"""

    def __init__(self, service: LedgerService) -> None:
        """保存本地账本服务引用。"""
        self._service = service

    def list_recent_bills(self, params: dict[str, object]) -> list[dict[str, object]]:
        """将后端风格查询转发到本地账本服务。"""
        return self._service.list_recent_bills(
            limit=int(params.get("limit", 5)),
            kind=str(params["kind"]) if params.get("kind") else None,
            category=str(params["category"]) if params.get("category") else None,
        )


class LocalStatQueryAdapter:
    """在图测试中用本地账本模拟后端统计服务。"""

    def __init__(self, service: LedgerService) -> None:
        """保存本地账本服务引用。"""
        self._service = service

    def summarize_bills(self, params: dict[str, object]) -> dict[str, object]:
        """将后端风格统计转发到本地账本服务。"""
        return self._service.summarize_bills(
            kind=str(params["kind"]) if params.get("kind") else None,
            category=str(params["category"]) if params.get("category") else None,
        )


class LedgerServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        """准备独立的 JSON 账本并写入测试样例数据。"""
        self.runtime_dir = ROOT_RUNTIME_DIR
        self.runtime_dir.mkdir(exist_ok=True)
        self.ledger_path = self.runtime_dir / f"ledger_{uuid4().hex}.json"
        os.environ["ACCOUNT_AGENT_LEDGER_PATH"] = str(self.ledger_path)
        os.environ["ACCOUNT_AGENT_MODEL"] = "fake-vision-model"
        get_settings.cache_clear()
        get_bill_command_service.cache_clear()
        get_bill_query_service.cache_clear()
        get_stat_query_service.cache_clear()

        self.service = LedgerService(JsonLedgerStore(self.ledger_path))
        self.bill_command_service = LocalBillCommandAdapter(self.service)
        self.bill_query_service = LocalBillQueryAdapter(self.service)
        self.stat_query_service = LocalStatQueryAdapter(self.service)
        self.command_patcher = patch(
            "account_agent.tools.ledger_tools.get_bill_command_service",
            return_value=self.bill_command_service,
        )
        self.query_patcher = patch(
            "account_agent.tools.ledger_tools.get_bill_query_service",
            return_value=self.bill_query_service,
        )
        self.stat_patcher = patch(
            "account_agent.tools.ledger_tools.get_stat_query_service",
            return_value=self.stat_query_service,
        )
        self.command_patcher.start()
        self.query_patcher.start()
        self.stat_patcher.start()
        self.service.add_bill(
            amount=28,
            kind="expense",
            category="餐饮",
            note="lunch",
            occurred_at="2026-04-16T12:00:00",
        )
        self.service.add_bill(
            amount=66,
            kind="expense",
            category="交通",
            note="taxi",
            occurred_at="2026-04-16T18:30:00",
        )
        self.service.add_bill(
            amount=12000,
            kind="income",
            category="工资",
            note="salary",
            occurred_at="2026-04-15T09:00:00",
        )

    def tearDown(self) -> None:
        """清理缓存配置并删除临时账本文件。"""
        self.command_patcher.stop()
        self.query_patcher.stop()
        self.stat_patcher.stop()
        get_settings.cache_clear()
        os.environ.pop("ACCOUNT_AGENT_LEDGER_PATH", None)
        os.environ.pop("ACCOUNT_AGENT_MODEL", None)
        os.environ.pop("ACCOUNT_AGENT_API_KEY", None)
        os.environ.pop("ACCOUNT_AGENT_BASE_URL", None)
        get_bill_command_service.cache_clear()
        get_bill_query_service.cache_clear()
        get_stat_query_service.cache_clear()
        if self.ledger_path.exists():
            self.ledger_path.unlink()

    def test_add_bill_success(self) -> None:
        """新增账单时应完成规范化并成功落盘。"""
        bill = self.service.add_bill(
            amount=18.5,
            kind="expense",
            category="food",
            note="breakfast",
            occurred_at="2026-04-17T08:30:00",
        )

        self.assertEqual(bill["kind"], "expense")
        self.assertEqual(bill["category"], "餐饮")
        self.assertEqual(bill["amount"], 18.5)

    def test_list_recent_bills_success(self) -> None:
        """最近账单应按时间倒序返回。"""
        recent = self.service.list_recent_bills(limit=2)

        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0]["category"], "交通")
        self.assertEqual(recent[1]["category"], "餐饮")

    def test_summarize_bills_success(self) -> None:
        """支出汇总应按分类聚合金额。"""
        summary = self.service.summarize_bills(kind="expense")

        self.assertEqual(summary["count"], 2)
        self.assertEqual(summary["total_amount"], 94.0)
        self.assertEqual(summary["by_category"]["交通"], 66.0)
        self.assertEqual(summary["by_category"]["餐饮"], 28.0)

    def test_build_graph_for_deployment_success(self) -> None:
        """可部署图入口应能够成功调用。"""
        agent = build_graph(model=ToolFriendlyFakeListChatModel(responses=["部署入口可用"]))
        result = agent.invoke({"messages": [HumanMessage(content="你好")]})

        self.assertEqual(result["messages"][-1].content, "部署入口可用")

    def test_build_graph_accepts_model_dict_success(self) -> None:
        """图构建函数应支持传入模型配置字典。"""
        agent = build_graph(
            model={
                "model": "qwen3.5-flash",
                "temperature": 0,
                "api_key": "test-api-key",
                "base_url": "https://example.com/v1",
            }
        )

        self.assertEqual(type(agent).__name__, "CompiledStateGraph")

    def test_create_local_agent_success(self) -> None:
        """本地图入口应能配合内存 checkpoint 正常工作。"""
        agent = create_local_agent(model=ToolFriendlyFakeListChatModel(responses=["本地入口可用"]))
        result = agent.invoke(
            {"messages": [HumanMessage(content="你好")]},
            config={"configurable": {"thread_id": "test-thread"}},
        )

        self.assertEqual(result["messages"][-1].content, "本地入口可用")

    def test_text_add_bill_uses_model_generated_receipt_reply(self) -> None:
        """文本记账流程应返回模型生成的回执回复。"""
        self._reset_empty_ledger()
        agent = create_local_agent(model=TextAddBillReplyModel())

        result = agent.invoke(
            {"messages": [HumanMessage(content="工资发了2000")]},
            config={"configurable": {"thread_id": "text-add-thread"}},
        )

        store = JsonLedgerStore(self.ledger_path)
        bills = store.list_bills()
        self.assertEqual(len(bills), 1)
        self.assertEqual(bills[0].kind, "income")
        self.assertEqual(bills[0].category, "工资")
        self.assertIn("已帮你记下这笔收入", result["messages"][-1].content)
        self.assertIn("2000.0 元", result["messages"][-1].content)

    def test_text_multi_add_bill_uses_all_saved_results_in_reply(self) -> None:
        """一轮新增多笔账时，最终回执应覆盖全部成功账单。"""
        self._reset_empty_ledger()
        agent = create_local_agent(model=MultiAddBillReplyModel())

        result = agent.invoke(
            {"messages": [HumanMessage(content="吃饭 40，工资发了 22222")]},
            config={"configurable": {"thread_id": "text-multi-add-thread"}},
        )

        store = JsonLedgerStore(self.ledger_path)
        bills = store.list_bills()
        self.assertEqual(len(bills), 2)
        reply = result["messages"][-1].content
        self.assertIn("2 笔账", reply)
        self.assertIn("40.0 元", reply)
        self.assertIn("22222.0 元", reply)

    def test_recent_add_bill_payloads_do_not_cross_into_previous_turn(self) -> None:
        """统计或查询工具结果不应误读上一轮的记账回执。"""
        state = {
            "messages": [
                HumanMessage(content="吃饭30，工资100"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {"name": "add_bill", "args": {"amount": 30}, "id": "call_1", "type": "tool_call"},
                        {"name": "add_bill", "args": {"amount": 100}, "id": "call_2", "type": "tool_call"},
                    ],
                ),
                ToolMessage(
                    name="add_bill",
                    tool_call_id="call_1",
                    content=json.dumps(
                        {"ok": True, "bill": {"id": "1", "amount": 30.0, "kind": "expense", "category": "餐饮"}}
                    ),
                ),
                ToolMessage(
                    name="add_bill",
                    tool_call_id="call_2",
                    content=json.dumps(
                        {"ok": True, "bill": {"id": "2", "amount": 100.0, "kind": "income", "category": "工资"}}
                    ),
                ),
                AIMessage(content="已帮你记下 2 笔账。"),
                HumanMessage(content="帮我统计一下最近两笔账单"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "summarize_bills",
                            "args": {"kind": None, "category": None},
                            "id": "call_3",
                            "type": "tool_call",
                        }
                    ],
                ),
                ToolMessage(
                    name="summarize_bills",
                    tool_call_id="call_3",
                    content=json.dumps(
                        {"ok": True, "summary": {"count": 2, "total_amount": 130.0, "by_kind": {"income": 100, "expense": 30}}}
                    ),
                ),
            ]
        }

        self.assertEqual(_recent_add_bill_payloads(state), [])

    def test_normalize_image_blocks_uses_openai_image_url_shape(self) -> None:
        """图片块应规范化为 OpenAI 兼容的 image_url 结构。"""
        image_base64 = base64.b64encode((FIXTURES_DIR / "restaurant_receipt.jpg").read_bytes()).decode("utf-8")

        normalized = ImageAnalysisService._normalize_image_blocks(
            [{"type": "image", "base64": image_base64, "mime_type": "image/jpeg"}]
        )

        self.assertEqual(
            normalized,
            [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}",
                    },
                }
            ],
        )

    def test_image_auto_add_bill_success(self) -> None:
        """图片账单候选信息完整时应自动入账。"""
        self._reset_empty_ledger()
        agent = create_local_agent(model=ToolFriendlyFakeListChatModel(responses=[
            self._analysis_json(
                is_accounting_related=True,
                image_kind="receipt",
                raw_summary="麦当劳午餐小票",
                bill_candidate={
                    "amount": 28,
                    "kind": "expense",
                    "category": "餐饮",
                    "note": "麦当劳午餐",
                    "occurred_at": "2026-04-19T12:10:00",
                },
            ),
            "已为你记下一笔支出：28.0 元，分类餐饮，时间 2026-04-19 12:10，备注 麦当劳午餐。如果需要，我还可以继续帮你查询最近流水或做分类统计。",
        ]))

        result = agent.invoke(
            {"messages": [self._receipt_image_message("帮我看看这张图并记账")]},
            config={"configurable": {"thread_id": "image-auto-add-thread"}},
        )

        store = JsonLedgerStore(self.ledger_path)
        bills = store.list_bills()
        self.assertEqual(len(bills), 1)
        self.assertEqual(bills[0].amount, 28.0)
        self.assertEqual(bills[0].kind, "expense")
        self.assertEqual(bills[0].category, "餐饮")
        self.assertIn("已帮你记下这笔支出", result["messages"][-1].content)
        self.assertIn("28.0 元", result["messages"][-1].content)
        self.assertIn("时间 2026-04-19T12:10:00", result["messages"][-1].content)

    def test_image_irrelevant_does_not_add_bill(self) -> None:
        """与记账无关的图片不应生成账单。"""
        self._reset_empty_ledger()
        agent = create_local_agent(model=ToolFriendlyFakeListChatModel(responses=[self._analysis_json(
            is_accounting_related=False,
            image_kind="other",
            raw_summary="一只猫趴在桌面上",
            bill_candidate=None,
        )]))

        result = agent.invoke(
            {"messages": [self._receipt_image_message("这张图能记账吗")]},
            config={"configurable": {"thread_id": "image-irrelevant-thread"}},
        )

        store = JsonLedgerStore(self.ledger_path)
        bills = store.list_bills()
        self.assertEqual(len(bills), 0)
        self.assertIn("和记账无关", result["messages"][-1].content)

    def test_image_missing_fields_only_asks_question(self) -> None:
        """图片账单缺关键字段时应触发追问。"""
        self._reset_empty_ledger()
        agent = create_local_agent(model=ToolFriendlyFakeListChatModel(responses=[self._analysis_json(
            is_accounting_related=True,
            image_kind="receipt",
            raw_summary="打车订单截图，但没有明确金额",
            bill_candidate={
                "amount": None,
                "kind": "expense",
                "category": "交通",
                "note": "滴滴打车",
                "occurred_at": "2026-04-19T09:30:00",
            },
        )]))

        result = agent.invoke(
            {"messages": [self._receipt_image_message("请识别这张图")]},
            config={"configurable": {"thread_id": "image-missing-thread"}},
        )

        store = JsonLedgerStore(self.ledger_path)
        bills = store.list_bills()
        self.assertEqual(len(bills), 0)
        self.assertIn("还缺少", result["messages"][-1].content)
        self.assertIn("金额", result["messages"][-1].content)

    def test_image_missing_fields_then_user_supplements_and_adds_bill(self) -> None:
        """后续用户补充信息后应完成并保存待补全账单。"""
        self._reset_empty_ledger()
        agent = create_local_agent(model=PendingBillCompletionModel(responses=[
            self._analysis_json(
                is_accounting_related=True,
                image_kind="receipt",
                raw_summary="打车订单截图，但没有明确金额",
                bill_candidate={
                    "amount": None,
                    "kind": "expense",
                    "category": "交通",
                    "note": "滴滴打车",
                    "occurred_at": "2026-04-19T09:30:00",
                },
            ),
            "已为你记下一笔支出：36.0 元，分类交通，时间 2026-04-19 09:30，备注 滴滴打车。如果需要，我还可以继续帮你查询最近流水或做分类统计。",
        ]))
        thread_id = "image-fill-thread"

        first = agent.invoke(
            {"messages": [self._receipt_image_message("请识别这张图")]},
            config={"configurable": {"thread_id": thread_id}},
        )
        self.assertIn("还缺少", first["messages"][-1].content)

        second = agent.invoke(
            {"messages": [HumanMessage(content="金额 36，直接记账")]},
            config={"configurable": {"thread_id": thread_id}},
        )

        store = JsonLedgerStore(self.ledger_path)
        bills = store.list_bills()
        self.assertEqual(len(bills), 1)
        self.assertEqual(bills[0].amount, 36.0)
        self.assertEqual(bills[0].category, "交通")
        self.assertIn("已帮你记下这笔支出", second["messages"][-1].content)

    def test_image_income_candidate_maps_to_income_bill(self) -> None:
        """收入类图片凭证应生成收入账单。"""
        self._reset_empty_ledger()
        agent = create_local_agent(model=ToolFriendlyFakeListChatModel(responses=[
            self._analysis_json(
                is_accounting_related=True,
                image_kind="income_proof",
                raw_summary="工资到账短信截图",
                bill_candidate={
                    "amount": 12000,
                    "kind": "income",
                    "category": "工资",
                    "note": "四月工资",
                    "occurred_at": "2026-04-19T09:00:00",
                },
            ),
            "已为你记下一笔收入：12000.0 元，分类工资，时间 2026-04-19 09:00，备注 四月工资。如果需要，我还可以继续帮你查询最近流水或做分类统计。",
        ]))

        result = agent.invoke(
            {"messages": [self._receipt_image_message("帮我从图片里识别这笔收入")]},
            config={"configurable": {"thread_id": "image-income-thread"}},
        )

        store = JsonLedgerStore(self.ledger_path)
        bills = store.list_bills()
        self.assertEqual(len(bills), 1)
        self.assertEqual(bills[0].kind, "income")
        self.assertEqual(bills[0].category, "工资")
        self.assertIn("已帮你记下这笔收入", result["messages"][-1].content)
        self.assertIn("12000.0 元", result["messages"][-1].content)
        self.assertIn("时间 2026-04-19T09:00:00", result["messages"][-1].content)

    def test_image_analysis_requires_api_key(self) -> None:
        """未配置 API Key 时图片分析应快速失败。"""
        os.environ.pop("ACCOUNT_AGENT_MODEL", None)
        os.environ.pop("ACCOUNT_AGENT_API_KEY", None)
        os.environ.pop("DEEPSEEK_API_KEY", None)
        os.environ.pop("DEEPSEEK_BASE_URL", None)
        get_settings.cache_clear()

        service = ImageAnalysisService()
        with self.assertRaisesRegex(ValueError, "ACCOUNT_AGENT_API_KEY"):
            service.analyze(
                image_blocks=[
                    {
                        "type": "image",
                        "base64": base64.b64encode(b"fake").decode("utf-8"),
                        "mime_type": "image/jpeg",
                    }
                ],
                user_text="帮我识别这张图",
            )

    def test_text_request_does_not_call_image_analysis_service(self) -> None:
        """纯文本请求不应进入图片分析分支。"""
        agent = create_local_agent(
            model=ToolFriendlyFakeListChatModel(responses=["文本链路正常"]),
            analysis_service=ExplodingImageAnalysisService(),
        )

        result = agent.invoke(
            {"messages": [HumanMessage(content="查询最近 2 笔账单")]},
            config={"configurable": {"thread_id": "text-only-thread"}},
        )

        self.assertEqual(result["messages"][-1].content, "文本链路正常")

    def test_image_invalid_category_only_asks_question_without_real_fixture(self) -> None:
        """缺失分类时应先追问而不是直接保存。"""
        self._reset_empty_ledger()
        analysis_service = StubImageAnalysisService(
            {
                "is_accounting_related": True,
                "image_kind": "receipt",
                "raw_summary": "便利店购物小票",
                "bill_candidate": {
                    "amount": 35.0,
                    "kind": "expense",
                    "category": None,
                    "note": "便利店消费",
                    "occurred_at": "2026-04-20T10:00:00",
                },
                "missing_fields": ["category"],
            }
        )
        agent = create_local_agent(
            model=ToolFriendlyFakeListChatModel(responses=["unused"]),
            analysis_service=analysis_service,
        )

        result = agent.invoke(
            {"messages": [self._inline_image_message("识别这张图并记账")]},
            config={"configurable": {"thread_id": "image-invalid-category-thread"}},
        )

        store = JsonLedgerStore(self.ledger_path)
        bills = store.list_bills()
        self.assertEqual(len(bills), 0)
        self.assertEqual(len(analysis_service.calls), 1)
        self.assertIn("还缺少", result["messages"][-1].content)
        self.assertIn("分类", result["messages"][-1].content)

    def test_normalize_candidate_handles_string_and_negative_amount_without_image_file(self) -> None:
        """候选数据规范化应将负数字符串金额转成正数。"""
        service = ImageAnalysisService(llm=object())

        candidate = service._normalize_candidate(
            {
                "amount": "-28.6",
                "kind": "expense",
                "category": "food",
                "note": "晚饭",
                "occurred_at": "2026-04-20T19:30:00",
            }
        )

        self.assertEqual(candidate["amount"], 28.6)
        self.assertEqual(candidate["kind"], "expense")
        self.assertEqual(candidate["category"], "餐饮")

    def _reset_empty_ledger(self) -> None:
        """重置测试账本并清理缓存单例。"""
        if self.ledger_path.exists():
            self.ledger_path.unlink()
        get_settings.cache_clear()

    @staticmethod
    def _analysis_json(
        *,
        is_accounting_related: bool,
        image_kind: str,
        raw_summary: str,
        bill_candidate: dict[str, object] | None,
    ) -> str:
        """构造一份假的图片分析 JSON 结果。"""
        missing_fields = []
        if is_accounting_related:
            candidate = bill_candidate or {}
            missing_fields = [
                field
                for field in ("amount", "kind", "category")
                if candidate.get(field) in (None, "")
            ]
        return json.dumps(
            {
                "is_accounting_related": is_accounting_related,
                "image_kind": image_kind,
                "raw_summary": raw_summary,
                "bill_candidate": bill_candidate,
                "missing_fields": missing_fields,
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _receipt_image_message(text: str) -> HumanMessage:
        """使用真实收据夹具图片构造 HumanMessage。"""
        image_base64 = base64.b64encode((FIXTURES_DIR / "restaurant_receipt.jpg").read_bytes()).decode("utf-8")
        return HumanMessage(
            content=[
                {"type": "text", "text": text},
                {
                    "type": "image",
                    "base64": image_base64,
                    "mime_type": "image/jpeg",
                },
            ]
        )

    @staticmethod
    def _inline_image_message(text: str) -> HumanMessage:
        """使用内联假图片数据构造 HumanMessage。"""
        image_base64 = base64.b64encode(b"fake-image-bytes").decode("utf-8")
        return HumanMessage(
            content=[
                {"type": "text", "text": text},
                {
                    "type": "image",
                    "base64": image_base64,
                    "mime_type": "image/jpeg",
                },
            ]
        )


if __name__ == "__main__":
    unittest.main()
