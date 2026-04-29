from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


CATEGORY_ALIASES = {
    "food": "餐饮",
    "meal": "餐饮",
    "dining": "餐饮",
    "lunch": "餐饮",
    "dinner": "餐饮",
    "taxi": "交通",
    "bus": "交通",
    "subway": "交通",
    "transport": "交通",
    "shopping": "购物",
    "shop": "购物",
    "salary": "工资",
    "payroll": "工资",
    "rent": "住房",
    "housing": "住房",
}
CANONICAL_CATEGORIES = {"餐饮", "交通", "购物", "工资", "住房", "其他"}
REQUIRED_FIELDS = ("amount", "kind", "category")


class BillCandidate(BaseModel):
    amount: float | None = Field(default=None, description="账单金额，必须为正数。")
    kind: Literal["expense", "income"] | None = Field(
        default=None,
        description="收支类型，只能是 expense 或 income。",
    )
    category: str | None = Field(
        default=None,
        description="尽量归一化为 餐饮、交通、购物、工资、住房、其他。",
    )
    note: str = Field(default="", description="简洁备注。")
    occurred_at: str | None = Field(
        default=None,
        description="ISO-8601 时间字符串，无法确定时返回 null。",
    )

    @field_validator("amount", mode="before")
    @classmethod
    def normalize_amount(cls, value):
        """将候选金额归一化为正浮点数。"""
        if value in (None, ""):
            return None
        try:
            amount = round(abs(float(value)), 2)
        except (TypeError, ValueError):
            return None
        return amount or None

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(cls, value):
        """将候选收支类型归一化到支持的枚举值。"""
        if value in (None, ""):
            return None
        kind = str(value).strip().lower()
        return kind if kind in {"expense", "income"} else None

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value):
        """将候选分类归一化到规范分类集合。"""
        if value in (None, ""):
            return None
        category = str(value).strip()
        if category in CANONICAL_CATEGORIES:
            return category
        return CATEGORY_ALIASES.get(category.lower())

    @field_validator("note", mode="before")
    @classmethod
    def normalize_note(cls, value):
        """清理候选备注文本两端空白。"""
        return str(value or "").strip()

    @field_validator("occurred_at", mode="before")
    @classmethod
    def normalize_occurred_at(cls, value):
        """规范化可选的发生时间文本。"""
        if value in (None, ""):
            return None
        return str(value).strip() or None


class ImageAnalysisResult(BaseModel):
    is_accounting_related: bool = Field(
        description="图片是否和记账直接相关。",
    )
    image_kind: str = Field(
        default="other",
        description="图片类型，例如 receipt、invoice、bill_screenshot、income_proof、other。",
    )
    raw_summary: str = Field(
        default="",
        description="对图片内容的一句话总结。",
    )
    bill_candidate: BillCandidate | None = Field(
        default=None,
        description="若与记账相关，返回一笔账单候选；否则返回 null。",
    )
    missing_fields: list[str] = Field(
        default_factory=list,
        description="关键字段缺失列表，只允许 amount、kind、category。",
    )

    @field_validator("image_kind", mode="before")
    @classmethod
    def normalize_image_kind(cls, value):
        """确保图片类型始终是非空字符串。"""
        return str(value or "other").strip() or "other"

    @field_validator("raw_summary", mode="before")
    @classmethod
    def normalize_raw_summary(cls, value):
        """将原始摘要规范化为去空白文本。"""
        return str(value or "").strip()

    @field_validator("missing_fields", mode="before")
    @classmethod
    def normalize_missing_fields(cls, value):
        """仅保留支持的必填字段名。"""
        if not value:
            return []
        return [
            str(item)
            for item in value
            if str(item) in REQUIRED_FIELDS
        ]

    @model_validator(mode="after")
    def finalize_result(self):
        """在字段级校验后补全统一的图片分析结果结构。"""
        if not self.is_accounting_related:
            self.bill_candidate = None
            self.missing_fields = []
            self.raw_summary = self.raw_summary or "这张图片和记账无关，我先不为它记账。"
            return self

        if self.bill_candidate is None:
            self.missing_fields = list(REQUIRED_FIELDS)
            return self

        self.missing_fields = [
            field
            for field in REQUIRED_FIELDS
            if getattr(self.bill_candidate, field) in (None, "")
        ]
        self.raw_summary = self.raw_summary or self.bill_candidate.note
        return self
