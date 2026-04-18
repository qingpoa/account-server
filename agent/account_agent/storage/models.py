from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class BillRecord:
    id: str
    amount: float
    kind: str
    category: str
    note: str
    occurred_at: str
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "BillRecord":
        return cls(
            id=str(data["id"]),
            amount=float(data["amount"]),
            kind=str(data["kind"]),
            category=str(data["category"]),
            note=str(data.get("note", "")),
            occurred_at=str(data["occurred_at"]),
            created_at=str(data["created_at"]),
        )
