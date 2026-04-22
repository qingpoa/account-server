from __future__ import annotations

from typing import Any

import httpx

from account_agent.api.errors import AgentError
from account_agent.api.request_context import get_request_context
from account_agent.config import Settings, get_settings


class ServerClient:
    """封装 Agent 到 Java 服务端的通用 HTTP 调用能力。"""

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
        *,
        authorization: str | None = None,
        token: str | None = None,
    ) -> None:
        """创建服务端客户端，占位阶段只提供通用请求骨架。"""
        self._settings = settings or get_settings()
        self._client = client or httpx.Client(timeout=self._settings.server_timeout)
        self._authorization = authorization
        self._token = token

    @property
    def settings(self) -> Settings:
        """返回当前客户端使用的配置。"""
        return self._settings

    def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """发送 GET 请求，并解包后端统一响应。"""
        try:
            response = self._client.get(
                self._build_url(path),
                params=params,
                headers=self._build_headers(headers),
            )
        except httpx.RequestError as exc:
            raise AgentError(status_code=503, message="服务端请求失败") from exc
        return self._unwrap_response(response)

    def post(
        self,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """发送 POST 请求，并解包后端统一响应。"""
        try:
            response = self._client.post(
                self._build_url(path),
                json=json_body,
                headers=self._build_headers(headers),
            )
        except httpx.RequestError as exc:
            raise AgentError(status_code=503, message="服务端请求失败") from exc
        return self._unwrap_response(response)

    def _build_url(self, path: str) -> str:
        """拼接完整请求地址。"""
        if not self._settings.server_base_url:
            raise AgentError(status_code=500, message="ACCOUNT_AGENT_SERVER_BASE_URL is not configured")
        base_url = self._settings.server_base_url.rstrip("/")
        normalized_path = path if path.startswith("/") else f"/{path}"
        return f"{base_url}{normalized_path}"

    def _build_headers(self, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        """组装默认请求头，并优先使用显式传入的鉴权信息。"""
        headers = {
            "Accept": "application/json",
        }

        authorization = self._resolve_authorization()
        if authorization:
            headers["Authorization"] = authorization

        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _resolve_authorization(self) -> str | None:
        """按优先级解析当前要透传到服务端的鉴权信息。"""
        if self._authorization:
            return self._authorization
        if self._token:
            return f"Bearer {self._token}"
        context = get_request_context()
        if context.authorization:
            return context.authorization
        if context.token:
            return f"Bearer {context.token}"
        if self._settings.server_token:
            auth_mode = self._settings.server_auth_mode
            if auth_mode == "bearer":
                return f"Bearer {self._settings.server_token}"
            return self._settings.server_token
        return None

    def _unwrap_response(self, response: httpx.Response) -> Any:
        """按统一响应格式解包服务端返回结果。"""
        try:
            payload = response.json()
        except ValueError as exc:
            raise AgentError(status_code=500, message="服务端响应不是合法 JSON") from exc

        if not isinstance(payload, dict):
            raise AgentError(status_code=500, message="服务端响应格式不正确")

        code = payload.get("code", response.status_code)
        msg = str(payload.get("msg", "服务端请求失败"))
        data = payload.get("data")
        if code != 200:
            raise AgentError(status_code=int(code), message=msg)
        return data

    def close(self) -> None:
        """关闭底层 HTTP 客户端。"""
        self._client.close()
