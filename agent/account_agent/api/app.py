from __future__ import annotations

import json

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import HumanMessage

from account_agent.api.errors import AgentError
from account_agent.api.exception_handlers import GlobalExceptionHandlers
from account_agent.api.request_context import (
    RequestContext,
    clear_request_context,
    set_request_context,
)
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
    GlobalExceptionHandlers.register(app)

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

    def _build_request_context(request: Request) -> RequestContext:
        """从当前 HTTP 请求头中提取请求上下文。"""
        return RequestContext(
            authorization=request.headers.get("Authorization"),
            token=request.headers.get("token"),
        )

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

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health(request: Request) -> HealthResponse:
        """返回简单的健康检查结果。"""
        set_request_context(_build_request_context(request))
        try:
            return HealthResponse(data=HealthData())
        finally:
            clear_request_context()

    @app.post("/api/v1/agent/chat", response_model=ChatResponse)
    def chat(payload: ChatRequest, request: Request) -> ChatResponse:
        """处理简单的阻塞式文本对话接口。"""
        context = _build_request_context(request)
        set_request_context(context)
        try:
            thread_id = _resolve_thread_id(payload.thread_id)
            reply = app.state.agent_service.chat(
                user_input=payload.message,
                thread_id=thread_id,
                authorization=context.authorization,
                token=context.token,
            )
            return ChatResponse(data=ChatData(thread_id=thread_id, reply=reply))
        finally:
            clear_request_context()

    @app.post("/api/v1/chat/stream")
    def chat_stream(payload: ChatStreamRequest, request: Request):
        """处理支持可选 SSE 输出的主对话接口。"""
        context = _build_request_context(request)
        set_request_context(context)
        try:
            thread_id = _resolve_thread_id(payload.thread_id)
            blocks = _build_message_blocks(payload.message, payload.attachments)
            messages = [HumanMessage(content=blocks if len(blocks) > 1 or blocks[0]["type"] != "text" else payload.message)]

            if not payload.stream:
                reply = app.state.agent_service.chat_messages(
                    messages=messages,
                    thread_id=thread_id,
                    authorization=context.authorization,
                    token=context.token,
                )
                return JSONResponse(_success_payload({"thread_id": thread_id, "reply": reply}))

            def event_stream():
                """逐条输出智能体事件流生成的 SSE 数据帧。"""
                set_request_context(context)
                try:
                    for event in app.state.agent_service.stream_events(
                        messages=messages,
                        thread_id=thread_id,
                        authorization=context.authorization,
                        token=context.token,
                    ):
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
                finally:
                    clear_request_context()
                yield _encode_sse("[DONE]")

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
        except Exception:
            if payload.stream:
                clear_request_context()
            raise
        finally:
            if not payload.stream:
                clear_request_context()
            else:
                clear_request_context()

    @app.get("/api/v1/chat/history/{thread_id}")
    def chat_history(thread_id: str, request: Request):
        """返回指定线程 ID 对应的历史对话。"""
        set_request_context(_build_request_context(request))
        try:
            return _success_payload(app.state.agent_service.get_history(thread_id=thread_id))
        finally:
            clear_request_context()

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
