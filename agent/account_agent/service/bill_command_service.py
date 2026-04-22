from __future__ import annotations

from datetime import datetime
from typing import Any

from account_agent.api.errors import AgentError
from account_agent.server import ServerClient
from account_agent.service.category_service import CategoryService


KIND_TO_TYPE = {
    "income": 1,
    "expense": 2,
}

class BillCommandService:
    """封装账单写操作，并负责将 Agent 字段映射到后端请求结构。"""

    def __init__(self, client: ServerClient | None = None) -> None:
        """创建账单写操作服务。"""
        self._client = client or ServerClient()
        self._category_service = CategoryService(client=self._client)

    def add_bill(self, payload: dict[str, Any]) -> dict[str, Any]:
        """将账单参数转换为后端接口入参后发起新增请求。"""
        request_body = {
            "categoryId": self._resolve_category_id(payload),
            "amount": self._resolve_amount(payload),
            "type": self._resolve_type(payload),
            "remark": self._resolve_remark(payload),
            "recordTime": self._resolve_record_time(payload),
            "isAiGenerated": self._resolve_is_ai_generated(payload),
        }
        return self._client.post("/bill", json_body=request_body)

    def _resolve_category_id(self, payload: dict[str, Any]) -> int:
        """优先使用 categoryId，否则根据分类名称映射系统分类 ID。"""
        category_id = payload.get("categoryId")
        if category_id is not None:
            try:
                return int(category_id)
            except (TypeError, ValueError) as exc:
                raise AgentError(status_code=400, message="categoryId must be a number") from exc

        category_name = str(payload.get("category", "")).strip()
        bill_type = self._resolve_type(payload)
        if not category_name:
            raise AgentError(status_code=400, message="category or categoryId is required")
        return self._category_service.resolve_category_id(category_name=category_name, bill_type=bill_type)

    def _resolve_amount(self, payload: dict[str, Any]) -> float:
        """校验金额并统一保留两位小数。"""
        raw_amount = payload.get("amount")
        if raw_amount is None:
            raise AgentError(status_code=400, message="amount is required")
        try:
            amount = round(float(raw_amount), 2)
        except (TypeError, ValueError) as exc:
            raise AgentError(status_code=400, message="amount must be a number") from exc
        if amount <= 0:
            raise AgentError(status_code=400, message="amount must be greater than 0")
        return amount

    def _resolve_type(self, payload: dict[str, Any]) -> int:
        """优先使用后端 type，否则根据 kind 转换为后端枚举值。"""
        bill_type = payload.get("type")
        if bill_type is not None:
            try:
                normalized_type = int(bill_type)
            except (TypeError, ValueError) as exc:
                raise AgentError(status_code=400, message="type must be a number") from exc
            if normalized_type not in {1, 2}:
                raise AgentError(status_code=400, message="type must be 1 or 2")
            return normalized_type

        kind = str(payload.get("kind", "")).strip().lower()
        if not kind:
            raise AgentError(status_code=400, message="kind or type is required")
        normalized_type = KIND_TO_TYPE.get(kind)
        if normalized_type is None:
            raise AgentError(status_code=400, message="kind must be income or expense")
        return normalized_type

    def _resolve_remark(self, payload: dict[str, Any]) -> str:
        """兼容 agent 的 note 字段和后端的 remark 字段。"""
        raw_remark = payload.get("remark", payload.get("note", ""))
        return str(raw_remark).strip()

    def _resolve_record_time(self, payload: dict[str, Any]) -> str | None:
        """将时间统一转换为后端约定的 YYYY-MM-DD HH:mm:ss。"""
        raw_record_time = payload.get("recordTime", payload.get("occurred_at"))
        if raw_record_time in (None, ""):
            return None

        text = str(raw_record_time).strip()
        if not text:
            return None

        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
            except ValueError as exc:
                raise AgentError(
                    status_code=400,
                    message="recordTime must be ISO format or YYYY-MM-DD HH:mm:ss",
                ) from exc
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def _resolve_is_ai_generated(self, payload: dict[str, Any]) -> int:
        """默认为 AI 生成，也允许调用方显式覆盖。"""
        raw_value = payload.get("isAiGenerated", 0)
        try:
            value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise AgentError(status_code=400, message="isAiGenerated must be 0 or 1") from exc
        if value not in {0, 1}:
            raise AgentError(status_code=400, message="isAiGenerated must be 0 or 1")
        return value
