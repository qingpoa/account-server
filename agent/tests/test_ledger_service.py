from __future__ import annotations

import unittest
from pathlib import Path
from uuid import uuid4

from account_agent.service.ledger_service import LedgerService
from account_agent.storage import JsonLedgerStore


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


if __name__ == "__main__":
    unittest.main()
