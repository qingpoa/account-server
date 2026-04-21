from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import HumanMessage

from account_agent.api.errors import AgentError
from account_agent.api.schemas import (
    ChatRequest,
    ChatResponse,
    ChatData,
    ChatStreamRequest,
    HealthResponse,
    HealthData,
)
from account_agent.config import get_settings
from account_agent.service.agent_service import AccountingAgentService


def create_app(agent_service: AccountingAgentService | None = None) -> FastAPI:
    """创建供前端调用的 FastAPI 应用。"""
    app = FastAPI(
        title="Accounting Agent API",
        version="0.1.0",
        description="Frontend-facing API for the accounting LangGraph agent.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.agent_service = agent_service or AccountingAgentService()

    def _error_response(status_code: int, message: str) -> JSONResponse:
        """构造符合前端约定的统一错误响应。"""
        return JSONResponse(
            status_code=status_code,
            content={
                "code": status_code,
                "msg": message,
                "data": None,
            },
        )

    def _success_payload(data):
        """构造符合前端约定的统一成功响应体。"""
        return {
            "code": 200,
            "msg": "success",
            "data": data,
        }

    def _resolve_thread_id(thread_id: str | None) -> str:
        """解析当前请求实际生效的线程 ID。"""
        return thread_id or get_settings().default_thread_id

    def _encode_sse(payload: str) -> str:
        """将一段文本编码成单个 SSE 数据帧。"""
        return f"data: {payload}\n\n"

    def _build_message_blocks(message: str, attachments) -> list[dict[str, object]]:
        """将接口请求字段转换成 LangChain 多模态消息块。"""
        blocks: list[dict[str, object]] = []
        text = message.strip()
        if text:
            blocks.append({"type": "text", "text": text})
        for attachment in attachments:
            attachment_type = str(getattr(attachment, "type", "image")).strip().lower()
            if attachment_type != "image":
                raise AgentError(
                    status_code=400,
                    message=f"Unsupported attachment type for agent: {attachment_type}",
                )
            blocks.append(
                {
                    "type": "image_url",
                    "image_url": {"url": attachment.url},
                }
            )
        if not blocks:
            blocks.append({"type": "text", "text": "你好"})
        return blocks

    @app.exception_handler(AgentError)
    def handle_agent_error(_: Request, exc: AgentError) -> JSONResponse:
        """将业务异常转换为统一 JSON 错误响应。"""
        return _error_response(status_code=exc.status_code, message=exc.message)

    @app.exception_handler(RequestValidationError)
    def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        """将 FastAPI 参数校验异常映射为文档中的 400。"""
        first_error = exc.errors()[0] if exc.errors() else {}
        message = str(first_error.get("msg", "参数错误"))
        return _error_response(status_code=400, message=message)

    @app.exception_handler(HTTPException)
    def handle_http_error(_: Request, exc: HTTPException) -> JSONResponse:
        """兜底处理框架层抛出的 HTTP 异常。"""
        detail = exc.detail
        message = detail if isinstance(detail, str) else "请求处理失败"
        return _error_response(status_code=exc.status_code, message=message)

    @app.exception_handler(Exception)
    def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        """兜底处理未捕获异常，避免泄露默认 FastAPI 错误结构。"""
        return _error_response(status_code=500, message=str(exc) or "服务器内部错误")

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        """返回简单的健康检查结果。"""
        return HealthResponse(data=HealthData())

    @app.post("/api/v1/agent/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        """处理简单的阻塞式文本对话接口。"""
        thread_id = _resolve_thread_id(request.thread_id)
        reply = app.state.agent_service.chat(
            user_input=request.message,
            thread_id=thread_id,
        )
        return ChatResponse(data=ChatData(thread_id=thread_id, reply=reply))

    @app.post("/api/v1/chat/stream")
    def chat_stream(request: ChatStreamRequest):
        """处理支持可选 SSE 输出的主对话接口。"""
        thread_id = _resolve_thread_id(request.thread_id)
        blocks = _build_message_blocks(request.message, request.attachments)
        messages = [HumanMessage(content=blocks if len(blocks) > 1 or blocks[0]["type"] != "text" else request.message)]

        if not request.stream:
            reply = app.state.agent_service.chat_messages(messages=messages, thread_id=thread_id)
            return JSONResponse(_success_payload({"thread_id": thread_id, "reply": reply}))

        def event_stream():
            """逐条输出智能体事件流生成的 SSE 数据帧。"""
            try:
                for event in app.state.agent_service.stream_events(messages=messages, thread_id=thread_id):
                    yield _encode_sse(json.dumps(event, ensure_ascii=False))
            except AgentError as exc:
                error_event = {
                    "type": "error",
                    "code": exc.status_code,
                    "msg": exc.message,
                }
                yield _encode_sse(json.dumps(error_event, ensure_ascii=False))
            except Exception as exc:
                error_event = {
                    "type": "error",
                    "code": 500,
                    "msg": str(exc) or "服务器内部错误",
                }
                yield _encode_sse(json.dumps(error_event, ensure_ascii=False))
            yield _encode_sse("[DONE]")

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    @app.get("/api/v1/chat/history/{thread_id}")
    def chat_history(thread_id: str):
        """返回指定线程 ID 对应的历史对话。"""
        return _success_payload(app.state.agent_service.get_history(thread_id=thread_id))

    return app


app = create_app()


def main() -> None:
    """使用 uvicorn 启动 FastAPI 服务。"""
    import uvicorn

    uvicorn.run(
        "account_agent.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
