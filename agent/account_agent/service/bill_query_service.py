from __future__ import annotations

from datetime import datetime
from typing import Any

from account_agent.api.errors import AgentError
from account_agent.server import ServerClient
from account_agent.service.bill_command_service import KIND_TO_TYPE
from account_agent.service.category_service import CategoryService


TYPE_TO_KIND = {
    1: "income",
    2: "expense",
}


class BillQueryService:
    """封装账单读操作，并将后端响应映射为 Agent 使用的账单结构。"""

    def __init__(self, client: ServerClient | None = None) -> None:
        """创建账单查询服务。"""
        self._client = client or ServerClient()
        self._category_service = CategoryService(client=self._client)

    def list_recent_bills(self, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """查询最近流水，并将列表项转换为 Agent 使用的标准字段。"""
        request_params = self._build_list_params(params or {})
        data = self._client.get("/bill/list", params=request_params)
        if not isinstance(data, dict):
            raise AgentError(status_code=500, message="账单列表接口返回格式不正确")

        raw_items = data.get("list", [])
        if not isinstance(raw_items, list):
            raise AgentError(status_code=500, message="账单列表字段不是数组")
        return [self._map_bill_item(item) for item in raw_items]

    def _build_list_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """将 Agent 查询参数转换成后端 `/bill/list` 接口参数。"""
        limit = params.get("limit", params.get("pageSize", 5))
        try:
            page_size = max(1, int(limit))
        except (TypeError, ValueError) as exc:
            raise AgentError(status_code=400, message="limit must be a number") from exc

        request_params = {
            "pageNum": int(params.get("pageNum", 1)),
            "pageSize": page_size,
            "startTime": self._format_server_datetime(
                params.get("startTime", params.get("start_time"))
            ),
            "endTime": self._format_server_datetime(
                params.get("endTime", params.get("end_time"))
            ),
        }

        bill_type = self._resolve_type(params)
        if bill_type is not None:
            request_params["type"] = bill_type

        category_id = self._resolve_category_id(params, bill_type=bill_type)
        if category_id is not None:
            request_params["categoryId"] = category_id

        return {key: value for key, value in request_params.items() if value is not None}

    def _map_bill_item(self, item: Any) -> dict[str, Any]:
        """将后端账单列表项转换为 Agent 账单结构。"""
        if not isinstance(item, dict):
            raise AgentError(status_code=500, message="账单列表项格式不正确")

        raw_type = item.get("type")
        try:
            bill_type = int(raw_type)
        except (TypeError, ValueError) as exc:
            raise AgentError(status_code=500, message="账单类型字段无效") from exc

        kind = TYPE_TO_KIND.get(bill_type)
        if kind is None:
            raise AgentError(status_code=500, message=f"unsupported bill type: {bill_type}")

        occurred_at = self._to_iso_datetime(item.get("recordTime"))
        return {
            "id": str(item.get("id", "")),
            "amount": round(float(item.get("amount", 0)), 2),
            "kind": kind,
            "category": str(item.get("categoryName", "其他")),
            "note": str(item.get("remark", "")),
            "occurred_at": occurred_at,
            "created_at": occurred_at,
            "is_ai_generated": int(item.get("isAiGenerated", 0)),
        }

    def _resolve_type(self, params: dict[str, Any]) -> int | None:
        """将 kind 或 type 参数转换为后端枚举值。"""
        if "type" in params and params.get("type") is not None:
            try:
                bill_type = int(params["type"])
            except (TypeError, ValueError) as exc:
                raise AgentError(status_code=400, message="type must be a number") from exc
            if bill_type not in {1, 2}:
                raise AgentError(status_code=400, message="type must be 1 or 2")
            return bill_type

        kind = params.get("kind")
        if kind in (None, ""):
            return None
        normalized_kind = str(kind).strip().lower()
        bill_type = KIND_TO_TYPE.get(normalized_kind)
        if bill_type is None:
            raise AgentError(status_code=400, message="kind must be income or expense")
        return bill_type

    def _resolve_category_id(self, params: dict[str, Any], *, bill_type: int | None) -> int | None:
        """将 category 或 categoryId 参数转换为后端分类 ID。"""
        if "categoryId" in params and params.get("categoryId") is not None:
            try:
                return int(params["categoryId"])
            except (TypeError, ValueError) as exc:
                raise AgentError(status_code=400, message="categoryId must be a number") from exc

        category = params.get("category")
        if category in (None, ""):
            return None
        category_name = str(category).strip()
        if category_name == "其他":
            if bill_type is None:
                raise AgentError(status_code=400, message="kind or type is required when category is 其他")
        return self._category_service.resolve_category_id(category_name=category_name, bill_type=bill_type)

    @staticmethod
    def _format_server_datetime(value: Any) -> str | None:
        """将传入时间转换为后端约定的 YYYY-MM-DD HH:mm:ss。"""
        if value in (None, ""):
            return None
        text = str(value).strip()
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
            except ValueError as exc:
                raise AgentError(
                    status_code=400,
                    message="time must be ISO format or YYYY-MM-DD HH:mm:ss",
                ) from exc
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _to_iso_datetime(value: Any) -> str:
        """将后端返回时间转换为秒级 ISO 字符串。"""
        if value in (None, ""):
            return ""
        text = str(value).strip()
        try:
            dt = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.isoformat(timespec="seconds")
