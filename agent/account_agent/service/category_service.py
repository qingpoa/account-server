from __future__ import annotations

from typing import Any

from account_agent.api.errors import AgentError
from account_agent.server import ServerClient


class CategoryService:
    """封装系统分类查询与分类名称/ID 解析逻辑。"""

    def __init__(self, client: ServerClient | None = None) -> None:
        """创建分类服务。"""
        self._client = client or ServerClient()
        self._cache: dict[int | None, list[dict[str, Any]]] = {}

    def list_categories(self, bill_type: int | None = None) -> list[dict[str, Any]]:
        """读取后端系统分类列表，并在当前服务实例内做简单缓存。"""
        if bill_type not in self._cache:
            params = {"type": bill_type} if bill_type is not None else None
            data = self._client.get("/category/list", params=params)
            if not isinstance(data, list):
                raise AgentError(status_code=500, message="分类列表接口返回格式不正确")
            self._cache[bill_type] = [item for item in data if isinstance(item, dict)]
        return self._cache[bill_type]

    def resolve_category_id(self, category_name: str, bill_type: int) -> int:
        """根据分类名称和收支类型解析后端分类 ID。"""
        normalized_name = category_name.strip()
        if normalized_name == "其他":
            normalized_name = "其他收入" if bill_type == 1 else "其他支出"

        for category in self.list_categories(bill_type):
            if str(category.get("name", "")).strip() == normalized_name:
                return int(category["id"])
        raise AgentError(status_code=400, message=f"unsupported category: {normalized_name}")

    def resolve_category_name(self, category_id: int) -> str:
        """根据分类 ID 反查分类名称。"""
        for category in self.list_categories():
            try:
                current_id = int(category.get("id"))
            except (TypeError, ValueError):
                continue
            if current_id == category_id:
                return str(category.get("name", ""))
        raise AgentError(status_code=400, message=f"unsupported categoryId: {category_id}")
