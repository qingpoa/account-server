from datetime import datetime, timedelta, timezone

from langchain_core.tools import tool

CHINA_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Shanghai")


@tool
def get_current_time() -> dict[str, object]:
    """获取当前时间，用于解析今天、昨天、本周、上个月等相对时间范围。"""
    now = datetime.now(CHINA_TIMEZONE)
    return {
        "timezone": "Asia/Shanghai",
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "current_date": now.strftime("%Y-%m-%d"),
    }


def get_time_tools() -> list:
    """返回时间工具集合。"""
    return [get_current_time]
