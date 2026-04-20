from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from account_agent.config import get_settings
from account_agent.service.ledger_service import CATEGORY_ALIASES, VALID_KINDS


IMAGE_ANALYSIS_PROMPT = """
你是记账图片分析工具。

请先判断图片是否和记账有关，再识别其中的账单信息。只返回一个 JSON 对象，不要输出解释、Markdown 或代码块。

返回字段要求：
- is_accounting_related: 布尔值。只有收据、小票、发票、账单截图、收入凭证等和记账直接相关时为 true。
- image_kind: 字符串，例如 receipt、invoice、bill_screenshot、income_proof、other。
- raw_summary: 对图片内容的一句话总结。
- bill_candidate: 若和记账相关，返回一个对象；否则返回 null。
- missing_fields: 数组，只列出 amount、kind、category 这三个关键字段中仍然缺失的字段名。

bill_candidate 字段：
- amount: 数字，必须为正数；无法确定时返回 null。
- kind: 只能是 expense、income；无法判断时返回 null。
- category: 尽量归一化为 餐饮、交通、购物、工资、住房、其他；无法判断时返回 null。
- note: 简洁备注，尽量包含商户名、用途或摘要。
- occurred_at: ISO-8601 时间字符串，无法确定时返回 null。

如果图片和记账无关：
- is_accounting_related=false
- bill_candidate=null
- missing_fields=[]
""".strip()

JSON_BLOCK_PATTERN = re.compile(r"\{.*\}", re.DOTALL)
CANONICAL_CATEGORIES = {"餐饮", "交通", "购物", "工资", "住房", "其他"}


class ImageAnalysisService:
    def __init__(self, llm=None) -> None:
        self._settings = get_settings()
        self._llm = llm

    def analyze(
        self,
        *,
        image_blocks: Sequence[Mapping[str, object]],
        user_text: str = "",
    ) -> dict[str, object]:
        normalized_blocks = self._normalize_image_blocks(image_blocks)
        if not normalized_blocks:
            raise ValueError("未检测到可识别的图片内容")

        prompt = IMAGE_ANALYSIS_PROMPT
        if user_text.strip():
            prompt = f"{prompt}\n\n用户补充说明：{user_text.strip()}"

        response = self._get_llm().invoke(
            [
                HumanMessage(
                    content=[
                        {"type": "text", "text": prompt},
                        *normalized_blocks,
                    ]
                )
            ]
        )
        payload = self._parse_response(self._message_to_text(response.content))
        return self._normalize_result(payload)

    def _get_llm(self):
        if self._llm is not None:
            return self._llm

        model_name = self._settings.vision_model or self._settings.model
        api_key = self._settings.vision_api_key or self._settings.api_key
        base_url = self._settings.vision_base_url or self._settings.base_url
        if not api_key:
            raise ValueError(
                "未配置 API Key。请在 .env 中填写 ACCOUNT_AGENT_API_KEY。"
            )
        self._llm = ChatOpenAI(
            model=model_name,
            temperature=0,
            timeout=self._settings.request_timeout,
            api_key=api_key,
            base_url=base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        return self._llm

    @staticmethod
    def _normalize_image_blocks(
        image_blocks: Sequence[Mapping[str, object]],
    ) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        for block in image_blocks:
            block_type = str(block.get("type", "")).lower()
            if block_type == "image_url":
                image_url = block.get("image_url")
                if isinstance(image_url, str):
                    normalized.append({"type": "image_url", "image_url": {"url": image_url}})
                elif isinstance(image_url, Mapping) and image_url.get("url"):
                    normalized.append(
                        {"type": "image_url", "image_url": {"url": str(image_url["url"])}} 
                    )
                continue

            if block_type != "image":
                continue

            source = block.get("source")
            if isinstance(source, Mapping):
                source_type = str(source.get("type", "")).lower()
                if source_type == "url" and source.get("url"):
                    normalized.append(
                        {"type": "image_url", "image_url": {"url": str(source["url"])}} 
                    )
                    continue
                if source_type == "base64" and source.get("data"):
                    media_type = str(source.get("media_type") or source.get("mime_type") or "image/jpeg")
                    normalized.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{str(source['data'])}",
                            },
                        }
                    )
                    continue

            if block.get("url"):
                normalized.append(
                    {"type": "image_url", "image_url": {"url": str(block["url"])}} 
                )
                continue

            base64_data = block.get("base64") or block.get("data")
            mime_type = block.get("mime_type") or block.get("mimeType") or "image/jpeg"
            if base64_data:
                normalized.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{str(mime_type)};base64,{str(base64_data)}",
                        },
                    }
                )
        return normalized

    @staticmethod
    def _parse_response(text: str) -> dict[str, object]:
        stripped = text.strip()
        if not stripped:
            raise ValueError("图片分析模型没有返回结果")

        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            match = JSON_BLOCK_PATTERN.search(stripped)
            if not match:
                preview = stripped[:200]
                raise ValueError(f"图片分析模型没有返回合法 JSON，原始输出片段：{preview}")
            return json.loads(match.group(0))

    def _normalize_result(self, payload: Mapping[str, object]) -> dict[str, object]:
        is_accounting_related = bool(payload.get("is_accounting_related"))
        raw_summary = str(payload.get("raw_summary") or "").strip()
        image_kind = str(payload.get("image_kind") or "other").strip() or "other"
        candidate = payload.get("bill_candidate")
        normalized_candidate = self._normalize_candidate(candidate if isinstance(candidate, Mapping) else None)

        if not is_accounting_related:
            return {
                "is_accounting_related": False,
                "image_kind": image_kind,
                "bill_candidate": None,
                "missing_fields": [],
                "raw_summary": raw_summary or "这张图片和记账无关。",
            }

        missing_fields = [
            field
            for field in ("amount", "kind", "category")
            if not normalized_candidate or normalized_candidate.get(field) in (None, "")
        ]

        return {
            "is_accounting_related": True,
            "image_kind": image_kind,
            "bill_candidate": normalized_candidate,
            "missing_fields": missing_fields,
            "raw_summary": raw_summary or (normalized_candidate or {}).get("note", ""),
        }

    def _normalize_candidate(self, candidate: Mapping[str, object] | None) -> dict[str, object] | None:
        if candidate is None:
            return None

        amount = candidate.get("amount")
        normalized_amount: float | None
        if amount in (None, ""):
            normalized_amount = None
        else:
            try:
                normalized_amount = round(abs(float(amount)), 2)
            except (TypeError, ValueError):
                normalized_amount = None
            if normalized_amount == 0:
                normalized_amount = None

        raw_kind = candidate.get("kind")
        normalized_kind = None
        if raw_kind not in (None, ""):
            kind = str(raw_kind).strip().lower()
            if kind in VALID_KINDS:
                normalized_kind = kind

        raw_category = candidate.get("category")
        normalized_category = None
        if raw_category not in (None, ""):
            category = str(raw_category).strip()
            if category in CANONICAL_CATEGORIES:
                normalized_category = category
            else:
                normalized_category = CATEGORY_ALIASES.get(category.lower())

        note = str(candidate.get("note") or "").strip()
        occurred_at = candidate.get("occurred_at")
        normalized_occurred_at = None if occurred_at in (None, "") else str(occurred_at).strip()

        return {
            "amount": normalized_amount,
            "kind": normalized_kind,
            "category": normalized_category,
            "note": note,
            "occurred_at": normalized_occurred_at,
        }

    @staticmethod
    def _message_to_text(content: object) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, Mapping) and block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
            return "\n".join(part for part in parts if part).strip()
        return str(content)
