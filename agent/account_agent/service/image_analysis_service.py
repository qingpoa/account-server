from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from account_agent.config import get_settings
from account_agent.service.analysis_models import BillCandidate, ImageAnalysisResult


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


class ImageAnalysisService:
    def __init__(self, llm=None) -> None:
        """创建图片分析服务，可选择注入外部模型。"""
        self._settings = get_settings()
        self._llm = llm

    def analyze(
        self,
        *,
        image_blocks: Sequence[Mapping[str, object]],
        user_text: str = "",
    ) -> dict[str, object]:
        """分析图片内容并返回结构化记账结果。"""
        normalized_blocks = self._normalize_image_blocks(image_blocks)
        if not normalized_blocks:
            raise ValueError("未检测到可识别的图片内容")

        prompt = IMAGE_ANALYSIS_PROMPT
        if user_text.strip():
            prompt = f"{prompt}\n\n用户补充说明：{user_text.strip()}"

        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                *normalized_blocks,
            ]
        )
        llm = self._get_llm()

        if isinstance(llm, ChatOpenAI):
            try:
                result = llm.with_structured_output(ImageAnalysisResult).invoke([message])
                return self._coerce_result(result)
            except Exception:
                pass

        response = llm.invoke([message])
        return self._coerce_result(response.content)

    def _get_llm(self):
        """构建并缓存用于图片分析的多模态模型。"""
        if self._llm is not None:
            return self._llm

        model_name = self._settings.model
        api_key = self._settings.api_key
        base_url = self._settings.base_url
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
        )
        return self._llm

    @staticmethod
    def _normalize_image_blocks(
        image_blocks: Sequence[Mapping[str, object]],
    ) -> list[dict[str, object]]:
        """将支持的图片块形态转换为 OpenAI 兼容的 image_url 结构。"""
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
    def _normalize_candidate(candidate: Mapping[str, object] | None) -> dict[str, object] | None:
        """使用共享的 Pydantic 模型规范化账单候选数据。"""
        if candidate is None:
            return None
        return BillCandidate.model_validate(candidate).model_dump()

    @staticmethod
    def _message_to_text(content: object) -> str:
        """将模型消息内容拍平成纯文本。"""
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

    def _coerce_result(self, result: object) -> dict[str, object]:
        """将结构化输出或 JSON 文本统一转成结果模型。"""
        if isinstance(result, ImageAnalysisResult):
            return result.model_dump()

        if isinstance(result, Mapping):
            return ImageAnalysisResult.model_validate(result).model_dump()

        text = self._message_to_text(result).strip()
        if not text:
            raise ValueError("图片分析模型没有返回结果")

        try:
            return ImageAnalysisResult.model_validate_json(text).model_dump()
        except Exception:
            match = JSON_BLOCK_PATTERN.search(text)
            if not match:
                preview = text[:200]
                raise ValueError(f"图片分析模型没有返回合法 JSON，原始输出片段：{preview}")
            payload = json.loads(match.group(0))
            return ImageAnalysisResult.model_validate(payload).model_dump()
