from __future__ import annotations

import base64
import json
import os
import unittest
from pathlib import Path

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from account_agent.config import get_settings
from account_agent.graph import build_graph, create_local_agent
from account_agent.graph.builder import _recent_add_bill_payloads, close_local_checkpointer
from account_agent.service.image_analysis_service import ImageAnalysisService


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class ToolFriendlyFakeListChatModel(FakeListChatModel):
    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self


class ExplodingImageAnalysisService:
    def analyze(
        self,
        *,
        image_blocks: list[dict[str, object]],
        user_text: str = "",
    ) -> dict[str, object]:
        raise AssertionError("image analysis should not be called for text-only requests")


class StubImageAnalysisService:
    def __init__(self, result: dict[str, object]) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def analyze(
        self,
        *,
        image_blocks: list[dict[str, object]],
        user_text: str = "",
    ) -> dict[str, object]:
        self.calls.append(
            {
                "image_blocks": image_blocks,
                "user_text": user_text,
            }
        )
        return dict(self.result)


class GraphAndImageFlowTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime_dir = Path(__file__).resolve().parents[2] / "tests_runtime"
        self.runtime_dir.mkdir(exist_ok=True)
        self.checkpoint_path = self.runtime_dir / "graph_and_image_flow.sqlite"
        os.environ["ACCOUNT_AGENT_CHECKPOINT_PATH"] = str(self.checkpoint_path)
        os.environ["ACCOUNT_AGENT_MODEL"] = "fake-vision-model"
        get_settings.cache_clear()
        close_local_checkpointer()

    def tearDown(self) -> None:
        get_settings.cache_clear()
        close_local_checkpointer()
        os.environ.pop("ACCOUNT_AGENT_CHECKPOINT_PATH", None)
        os.environ.pop("ACCOUNT_AGENT_MODEL", None)
        os.environ.pop("ACCOUNT_AGENT_API_KEY", None)
        os.environ.pop("ACCOUNT_AGENT_BASE_URL", None)
        os.environ.pop("DEEPSEEK_API_KEY", None)
        os.environ.pop("DEEPSEEK_BASE_URL", None)
        for path in (
            self.checkpoint_path,
            Path(f"{self.checkpoint_path}-wal"),
            Path(f"{self.checkpoint_path}-shm"),
        ):
            if path.exists():
                path.unlink()

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

    def test_recent_add_bill_payloads_do_not_cross_into_previous_turn(self) -> None:
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

    def test_image_analysis_requires_api_key(self) -> None:
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

        self.assertEqual(len(analysis_service.calls), 1)
        self.assertIn("还缺少", result["messages"][-1].content)
        self.assertIn("分类", result["messages"][-1].content)

    def test_normalize_candidate_handles_string_and_negative_amount_without_image_file(self) -> None:
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

    @staticmethod
    def _inline_image_message(text: str) -> HumanMessage:
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
