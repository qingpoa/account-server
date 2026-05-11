from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from account_agent.api.errors import AgentError


SERVER_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


def format_server_datetime(value: Any, *, field_name: str = "time") -> str | None:
    """将时间值转换为后端接口约定的 YYYY-MM-DDTHH:mm:ss。"""
    dt = parse_datetime(value, field_name=field_name)
    if dt is None:
        return None
    return dt.strftime(SERVER_DATETIME_FORMAT)


def get_time_filter(filters: Mapping[str, Any], field_name: str) -> Any:
    """从筛选参数中读取 startTime/endTime，并兼容蛇形命名。"""
    if field_name == "startTime":
        return filters.get("startTime", filters.get("start_time"))
    if field_name == "endTime":
        return filters.get("endTime", filters.get("end_time"))
    return filters.get(field_name)


def build_time_params(filters: Mapping[str, Any]) -> dict[str, str | None]:
    """构造后端查询接口使用的时间筛选参数。"""
    return {
        "startTime": format_server_datetime(
            get_time_filter(filters, "startTime"),
            field_name="startTime",
        ),
        "endTime": format_server_datetime(
            get_time_filter(filters, "endTime"),
            field_name="endTime",
        ),
    }


def to_iso_datetime(value: Any) -> str:
    """将后端返回时间转换为秒级 ISO 字符串。"""
    dt = parse_datetime(value, field_name="recordTime")
    if dt is None:
        return ""
    return dt.isoformat(timespec="seconds")

def parse_datetime(value: Any, *, field_name: str = "time") -> datetime | None:
    """兼容解析 ISO 时间和 YYYY-MM-DD HH:mm:ss 时间。"""
    if value in (None, ""):
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            raise AgentError(
                status_code=400,
                message=f"{field_name} must be ISO format or YYYY-MM-DD HH:mm:ss",
            ) from exc
