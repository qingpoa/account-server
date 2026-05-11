from __future__ import annotations

from langchain_core.runnables import RunnableConfig


def resolve_request_auth(config: RunnableConfig | None) -> tuple[str | None, str | None]:
    """从 LangGraph configurable 中读取当前请求的鉴权信息。"""
    configurable = (config or {}).get("configurable", {})
    if not isinstance(configurable, dict):
        return None, None

    authorization = configurable.get("authorization")
    token = configurable.get("token")
    return (
        str(authorization).strip() if authorization else None,
        str(token).strip() if token else None,
    )
