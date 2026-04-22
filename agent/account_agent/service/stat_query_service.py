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


class StatQueryService:
    """封装统计查询操作，并将后端统计接口映射为 Agent 统计结构。"""

    def __init__(self, client: ServerClient | None = None) -> None:
        """创建统计查询服务。"""
        self._client = client or ServerClient()
        self._category_service = CategoryService(client=self._client)

    def summarize_bills(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """组合 overview/category/list 接口，生成与本地账本服务相近的统计结构。"""
        filters = params or {}
        bill_type = self._resolve_type(filters)
        category_name = self._resolve_category_name(filters)

        by_kind = self._build_by_kind(filters, bill_type=bill_type, category_name=category_name)
        by_category = self._build_by_category(filters, bill_type=bill_type, category_name=category_name)
        count = self._fetch_count(filters, bill_type=bill_type, category_name=category_name)
        total_amount = round(sum(by_kind.values()), 2)

        return {
            "count": count,
            "total_amount": total_amount,
            "kind": TYPE_TO_KIND.get(bill_type) if bill_type is not None else None,
            "category": category_name,
            "by_kind": {name: round(value, 2) for name, value in by_kind.items()},
            "by_category": {name: round(value, 2) for name, value in sorted(by_category.items())},
        }

    def _build_by_kind(
        self,
        filters: dict[str, Any],
        *,
        bill_type: int | None,
        category_name: str | None,
    ) -> dict[str, float]:
        """构造按收入/支出类型汇总的金额字典。"""
        if bill_type is not None:
            category_rows = self._fetch_category_rows(filters, bill_type)
            amount = self._sum_category_rows(category_rows, category_name)
            return {TYPE_TO_KIND[bill_type]: round(amount, 2)}

        if category_name:
            result: dict[str, float] = {}
            for current_type in (1, 2):
                rows = self._fetch_category_rows(filters, current_type)
                amount = self._sum_category_rows(rows, category_name)
                if amount > 0:
                    result[TYPE_TO_KIND[current_type]] = round(amount, 2)
            return result

        overview = self._fetch_overview(filters)
        return {
            "income": round(float(overview.get("totalIncome", 0)), 2),
            "expense": round(float(overview.get("totalExpense", 0)), 2),
        }

    def _build_by_category(
        self,
        filters: dict[str, Any],
        *,
        bill_type: int | None,
        category_name: str | None,
    ) -> dict[str, float]:
        """构造按分类汇总的金额字典。"""
        if bill_type is not None:
            return self._category_rows_to_map(
                self._fetch_category_rows(filters, bill_type),
                category_name=category_name,
            )

        result: dict[str, float] = {}
        for current_type in (1, 2):
            rows = self._fetch_category_rows(filters, current_type)
            for name, amount in self._category_rows_to_map(rows, category_name=category_name).items():
                result[name] = round(result.get(name, 0) + amount, 2)
        return result

    def _fetch_count(
        self,
        filters: dict[str, Any],
        *,
        bill_type: int | None,
        category_name: str | None,
    ) -> int:
        """通过账单列表接口读取当前筛选条件下的总条数。"""
        request_params = {
            "pageNum": 1,
            "pageSize": 1,
            "startTime": self._format_server_datetime(self._copy_time_filter(filters, "startTime")),
            "endTime": self._format_server_datetime(self._copy_time_filter(filters, "endTime")),
        }

        if bill_type is not None:
            request_params["type"] = bill_type

        category_id = self._resolve_category_id(category_name=category_name, bill_type=bill_type)
        if category_id is not None:
            if bill_type is not None:
                request_params["categoryId"] = category_id
                data = self._client.get("/bill/list", params=request_params)
                return int(data.get("total", 0)) if isinstance(data, dict) else 0

            total = 0
            for current_type in (1, 2):
                current_params = dict(request_params)
                current_params["type"] = current_type
                mapped_category_id = self._resolve_category_id(
                    category_name=category_name,
                    bill_type=current_type,
                )
                if mapped_category_id is not None:
                    current_params["categoryId"] = mapped_category_id
                data = self._client.get("/bill/list", params=current_params)
                if isinstance(data, dict):
                    total += int(data.get("total", 0))
            return total

        data = self._client.get("/bill/list", params=request_params)
        return int(data.get("total", 0)) if isinstance(data, dict) else 0

    def _fetch_overview(self, filters: dict[str, Any]) -> dict[str, Any]:
        """请求总览统计接口。"""
        data = self._client.get(
            "/stat/overview",
            params={
                "startTime": self._format_server_datetime(self._copy_time_filter(filters, "startTime")),
                "endTime": self._format_server_datetime(self._copy_time_filter(filters, "endTime")),
            },
        )
        if not isinstance(data, dict):
            raise AgentError(status_code=500, message="总览统计接口返回格式不正确")
        return data

    def _fetch_category_rows(self, filters: dict[str, Any], bill_type: int) -> list[dict[str, Any]]:
        """请求分类占比统计接口。"""
        data = self._client.get(
            "/stat/category",
            params={
                "type": bill_type,
                "startTime": self._format_server_datetime(self._copy_time_filter(filters, "startTime")),
                "endTime": self._format_server_datetime(self._copy_time_filter(filters, "endTime")),
            },
        )
        if not isinstance(data, list):
            raise AgentError(status_code=500, message="分类统计接口返回格式不正确")
        return [row for row in data if isinstance(row, dict)]

    def _category_rows_to_map(
        self,
        rows: list[dict[str, Any]],
        *,
        category_name: str | None,
    ) -> dict[str, float]:
        """将分类统计数组转换为分类金额映射。"""
        result: dict[str, float] = {}
        for row in rows:
            name = str(row.get("categoryName", "")).strip()
            if not name:
                continue
            if category_name and name != category_name:
                continue
            amount = round(float(row.get("amount", 0)), 2)
            result[name] = amount
        return result

    def _sum_category_rows(self, rows: list[dict[str, Any]], category_name: str | None) -> float:
        """汇总分类统计数组中的金额。"""
        if category_name:
            return round(
                sum(
                    float(row.get("amount", 0))
                    for row in rows
                    if str(row.get("categoryName", "")).strip() == category_name
                ),
                2,
            )
        return round(sum(float(row.get("amount", 0)) for row in rows), 2)

    def _resolve_type(self, filters: dict[str, Any]) -> int | None:
        """将 kind 或 type 筛选条件转换为后端枚举值。"""
        raw_type = filters.get("type")
        if raw_type is not None:
            try:
                bill_type = int(raw_type)
            except (TypeError, ValueError) as exc:
                raise AgentError(status_code=400, message="type must be a number") from exc
            if bill_type not in {1, 2}:
                raise AgentError(status_code=400, message="type must be 1 or 2")
            return bill_type

        kind = filters.get("kind")
        if kind in (None, ""):
            return None
        bill_type = KIND_TO_TYPE.get(str(kind).strip().lower())
        if bill_type is None:
            raise AgentError(status_code=400, message="kind must be income or expense")
        return bill_type

    def _resolve_category_name(self, filters: dict[str, Any]) -> str | None:
        """优先使用 category 名称，兼容 categoryId 反查分类名称。"""
        category = filters.get("category")
        if category not in (None, ""):
            return str(category).strip()

        category_id = filters.get("categoryId")
        if category_id in (None, ""):
            return None
        try:
            normalized_id = int(category_id)
        except (TypeError, ValueError) as exc:
            raise AgentError(status_code=400, message="categoryId must be a number") from exc
        return self._category_service.resolve_category_name(normalized_id)

    def _resolve_category_id(self, *, category_name: str | None, bill_type: int | None) -> int | None:
        """根据分类名称和类型推导后端分类 ID。"""
        if not category_name:
            return None
        normalized_name = category_name
        if normalized_name == "其他":
            if bill_type is None:
                raise AgentError(status_code=400, message="kind or type is required when category is 其他")
        return self._category_service.resolve_category_id(category_name=normalized_name, bill_type=bill_type)

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
    def _copy_time_filter(filters: dict[str, Any], field_name: str) -> Any:
        """透传 startTime/endTime，兼容蛇形命名。"""
        if field_name == "startTime":
            return filters.get("startTime", filters.get("start_time"))
        return filters.get("endTime", filters.get("end_time"))
