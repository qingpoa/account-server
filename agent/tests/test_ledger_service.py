from __future__ import annotations

import base64
import json
import os
import unittest
from pathlib import Path
from uuid import uuid4

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from account_agent.config import get_settings
from account_agent.graph import build_graph, create_local_agent
from account_agent.service.image_analysis_service import ImageAnalysisService
from account_agent.service.ledger_service import LedgerService
from account_agent.storage import JsonLedgerStore
from account_agent.tools.ledger_tools import get_ledger_service


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
ROOT_RUNTIME_DIR = Path(__file__).resolve().parents[2] / "tests_runtime"


class ToolFriendlyFakeListChatModel(FakeListChatModel):
    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self


class PendingBillCompletionModel(ToolFriendlyFakeListChatModel):
    def invoke(self, input, config=None, **kwargs):
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


class LedgerServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime_dir = ROOT_RUNTIME_DIR
        self.runtime_dir.mkdir(exist_ok=True)
        self.ledger_path = self.runtime_dir / f"ledger_{uuid4().hex}.json"
        os.environ["ACCOUNT_AGENT_LEDGER_PATH"] = str(self.ledger_path)
        os.environ["ACCOUNT_AGENT_VISION_MODEL"] = "fake-vision-model"
        get_settings.cache_clear()
        get_ledger_service.cache_clear()

        self.service = LedgerService(JsonLedgerStore(self.ledger_path))
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
        get_settings.cache_clear()
        get_ledger_service.cache_clear()
        os.environ.pop("ACCOUNT_AGENT_LEDGER_PATH", None)
        os.environ.pop("ACCOUNT_AGENT_VISION_MODEL", None)
        os.environ.pop("ACCOUNT_AGENT_API_KEY", None)
        os.environ.pop("ACCOUNT_AGENT_BASE_URL", None)
        if self.ledger_path.exists():
            self.ledger_path.unlink()

    def test_add_bill_success(self) -> None:
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
        recent = self.service.list_recent_bills(limit=2)

        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0]["category"], "交通")
        self.assertEqual(recent[1]["category"], "餐饮")

    def test_summarize_bills_success(self) -> None:
        summary = self.service.summarize_bills(kind="expense")

        self.assertEqual(summary["count"], 2)
        self.assertEqual(summary["total_amount"], 94.0)
        self.assertEqual(summary["by_category"]["交通"], 66.0)
        self.assertEqual(summary["by_category"]["餐饮"], 28.0)

    def test_build_graph_for_deployment_success(self) -> None:
        agent = build_graph(model=ToolFriendlyFakeListChatModel(responses=["部署入口可用"]))
        result = agent.invoke({"messages": [HumanMessage(content="你好")]})

        self.assertEqual(result["messages"][-1].content, "部署入口可用")

    def test_build_graph_accepts_model_dict_success(self) -> None:
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
        agent = create_local_agent(model=ToolFriendlyFakeListChatModel(responses=["本地入口可用"]))
        result = agent.invoke(
            {"messages": [HumanMessage(content="你好")]},
            config={"configurable": {"thread_id": "test-thread"}},
        )

        self.assertEqual(result["messages"][-1].content, "本地入口可用")

    def test_normalize_image_blocks_uses_openai_image_url_shape(self) -> None:
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
        self._reset_empty_ledger()
        agent = create_local_agent(model=ToolFriendlyFakeListChatModel(responses=[self._analysis_json(
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
        )]))

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
        self.assertIn("记账成功", result["messages"][-1].content)

    def test_image_irrelevant_does_not_add_bill(self) -> None:
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
        self._reset_empty_ledger()
        agent = create_local_agent(model=PendingBillCompletionModel(responses=[self._analysis_json(
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
        self.assertIn("记账成功", second["messages"][-1].content)

    def test_image_income_candidate_maps_to_income_bill(self) -> None:
        self._reset_empty_ledger()
        agent = create_local_agent(model=ToolFriendlyFakeListChatModel(responses=[self._analysis_json(
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
        )]))

        result = agent.invoke(
            {"messages": [self._receipt_image_message("帮我从图片里识别这笔收入")]},
            config={"configurable": {"thread_id": "image-income-thread"}},
        )

        store = JsonLedgerStore(self.ledger_path)
        bills = store.list_bills()
        self.assertEqual(len(bills), 1)
        self.assertEqual(bills[0].kind, "income")
        self.assertEqual(bills[0].category, "工资")
        self.assertIn("记账成功", result["messages"][-1].content)

    def test_image_analysis_requires_api_key(self) -> None:
        os.environ.pop("ACCOUNT_AGENT_VISION_MODEL", None)
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

    def _reset_empty_ledger(self) -> None:
        if self.ledger_path.exists():
            self.ledger_path.unlink()
        get_settings.cache_clear()
        get_ledger_service.cache_clear()

    @staticmethod
    def _analysis_json(
        *,
        is_accounting_related: bool,
        image_kind: str,
        raw_summary: str,
        bill_candidate: dict[str, object] | None,
    ) -> str:
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


if __name__ == "__main__":
    unittest.main()
