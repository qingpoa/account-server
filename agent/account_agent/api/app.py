from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import HumanMessage

from account_agent.api.schemas import (
    ChatRequest,
    ChatResponse,
    ChatStreamRequest,
    HealthResponse,
)
from account_agent.config import get_settings
from account_agent.service.agent_service import AccountingAgentService


def create_app(agent_service: AccountingAgentService | None = None) -> FastAPI:
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

    def _resolve_thread_id(thread_id: str | None) -> str:
        return thread_id or get_settings().default_thread_id

    def _encode_sse(payload: str) -> str:
        return f"data: {payload}\n\n"

    def _build_message_blocks(message: str, attachments) -> list[dict[str, object]]:
        blocks: list[dict[str, object]] = []
        text = message.strip()
        if text:
            blocks.append({"type": "text", "text": text})
        for attachment in attachments:
            attachment_type = str(getattr(attachment, "type", "image")).strip().lower()
            if attachment_type != "image":
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported attachment type for agent: {attachment_type}",
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
    def health() -> HealthResponse:
        return HealthResponse()

    @app.post("/api/v1/agent/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        thread_id = _resolve_thread_id(request.thread_id)
        reply = app.state.agent_service.chat(
            user_input=request.message,
            thread_id=thread_id,
        )
        return ChatResponse(thread_id=thread_id, reply=reply)

    @app.post("/api/v1/chat/stream")
    def chat_stream(request: ChatStreamRequest):
        thread_id = _resolve_thread_id(request.thread_id)
        blocks = _build_message_blocks(request.message, request.attachments)
        messages = [HumanMessage(content=blocks if len(blocks) > 1 or blocks[0]["type"] != "text" else request.message)]

        if not request.stream:
            reply = app.state.agent_service.chat_messages(messages=messages, thread_id=thread_id)
            return JSONResponse(
                {
                    "code": 200,
                    "msg": "success",
                    "data": {
                        "thread_id": thread_id,
                        "reply": reply,
                    },
                }
            )

        def event_stream():
            for event in app.state.agent_service.stream_events(messages=messages, thread_id=thread_id):
                yield _encode_sse(json.dumps(event, ensure_ascii=False))
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
        return {
            "code": 200,
            "msg": "success",
            "data": app.state.agent_service.get_history(thread_id=thread_id),
        }

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(
        "account_agent.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
