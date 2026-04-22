from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from account_agent.api.errors import AgentError


class GlobalExceptionHandlers:
    """统一管理 FastAPI 全局异常处理器。"""

    @staticmethod
    def error_response(status_code: int, message: str) -> JSONResponse:
        """构造符合前端约定的统一错误响应。"""
        return JSONResponse(
            status_code=status_code,
            content={
                "code": status_code,
                "msg": message,
                "data": None,
            },
        )

    @staticmethod
    def handle_agent_error(_: Request, exc: AgentError) -> JSONResponse:
        """将业务异常转换为统一 JSON 错误响应。"""
        return GlobalExceptionHandlers.error_response(
            status_code=exc.status_code,
            message=exc.message,
        )

    @staticmethod
    def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        """将 FastAPI 参数校验异常映射为文档中的 400。"""
        first_error = exc.errors()[0] if exc.errors() else {}
        message = str(first_error.get("msg", "参数错误"))
        return GlobalExceptionHandlers.error_response(status_code=400, message=message)

    @staticmethod
    def handle_http_error(_: Request, exc: HTTPException) -> JSONResponse:
        """兜底处理框架层抛出的 HTTP 异常。"""
        detail = exc.detail
        message = detail if isinstance(detail, str) else "请求处理失败"
        return GlobalExceptionHandlers.error_response(
            status_code=exc.status_code,
            message=message,
        )

    @staticmethod
    def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        """兜底处理未捕获异常，避免泄露默认 FastAPI 错误结构。"""
        return GlobalExceptionHandlers.error_response(
            status_code=500,
            message=str(exc) or "服务器内部错误",
        )

    @classmethod
    def register(cls, app: FastAPI) -> None:
        """向 FastAPI 应用注册全部全局异常处理器。"""
        app.add_exception_handler(AgentError, cls.handle_agent_error)
        app.add_exception_handler(RequestValidationError, cls.handle_validation_error)
        app.add_exception_handler(HTTPException, cls.handle_http_error)
        app.add_exception_handler(Exception, cls.handle_unexpected_error)
