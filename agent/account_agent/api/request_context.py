from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass


@dataclass(slots=True)
class RequestContext:
    """保存当前请求链路中需要向下透传的上下文信息。"""

    authorization: str | None = None
    token: str | None = None


_request_context: ContextVar[RequestContext] = ContextVar(
    "account_agent_request_context",
    default=RequestContext(),
)


def set_request_context(context: RequestContext) -> Token[RequestContext]:
    """设置当前请求上下文，并返回可用于回滚的 token。"""
    return _request_context.set(context)


def get_request_context() -> RequestContext:
    """读取当前请求上下文。"""
    return _request_context.get()


def reset_request_context(token: Token[RequestContext]) -> None:
    """使用 token 回滚当前请求上下文。"""
    _request_context.reset(token)


def clear_request_context() -> None:
    """将当前请求上下文清空为默认值。"""
    _request_context.set(RequestContext())
