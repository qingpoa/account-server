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
        """将账单记录转换为普通字典。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "BillRecord":
        """根据普通字典构建账单记录对象。"""
        return cls(
            id=str(data["id"]),
            amount=float(data["amount"]),
            kind=str(data["kind"]),
            category=str(data["category"]),
            note=str(data.get("note", "")),
            occurred_at=str(data["occurred_at"]),
            created_at=str(data["created_at"]),
        )
