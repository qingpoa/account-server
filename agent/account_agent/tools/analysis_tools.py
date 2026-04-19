from __future__ import annotations

from collections.abc import Mapping

from langchain_core.tools import tool

from account_agent.service import ImageAnalysisService


def get_analysis_tools(analysis_service: ImageAnalysisService) -> list:
    @tool
    def analyze_accounting_image(
        user_text: str = "",
        image_blocks: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        """Analyze image blocks and determine whether they are accounting-related."""
        blocks = image_blocks or []
        normalized_blocks = [
            dict(block)
            for block in blocks
            if isinstance(block, Mapping)
        ]
        return analysis_service.analyze(
            user_text=user_text,
            image_blocks=normalized_blocks,
        )

    return [analyze_accounting_image]
