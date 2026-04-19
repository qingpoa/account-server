from __future__ import annotations

import unittest
from pathlib import Path
from uuid import uuid4

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import HumanMessage

from account_agent.graph import build_graph, create_local_agent
from account_agent.service.ledger_service import LedgerService
from account_agent.storage import JsonLedgerStore


class ToolFriendlyFakeListChatModel(FakeListChatModel):
    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self


class LedgerServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime_dir = Path("tests_runtime")
        self.runtime_dir.mkdir(exist_ok=True)
        self.ledger_path = self.runtime_dir / f"ledger_{uuid4().hex}.json"
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
        agent = build_graph(model={"model": "deepseek-chat", "temperature": 0})

        self.assertEqual(type(agent).__name__, "CompiledStateGraph")

    def test_create_local_agent_success(self) -> None:
        agent = create_local_agent(model=ToolFriendlyFakeListChatModel(responses=["本地入口可用"]))
        result = agent.invoke(
            {"messages": [HumanMessage(content="你好")]},
            config={"configurable": {"thread_id": "test-thread"}},
        )

        self.assertEqual(result["messages"][-1].content, "本地入口可用")


if __name__ == "__main__":
    unittest.main()
