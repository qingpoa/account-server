from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    ok: bool = True
    status: str = "ok"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="User text input.")
    thread_id: str | None = Field(default=None, description="Conversation thread id.")


class ChatResponse(BaseModel):
    ok: bool = True
    thread_id: str
    reply: str


class AttachmentInput(BaseModel):
    type: str = Field(default="image", description="Attachment type, currently only image is supported.")
    url: str = Field(min_length=1, description="Publicly accessible attachment URL.")


class ChatStreamRequest(BaseModel):
    message: str = Field(min_length=1, description="User input.")
    thread_id: str = Field(min_length=1, description="Conversation thread id.")
    stream: bool = Field(default=True, description="Whether to enable SSE streaming.")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional context metadata.")
    attachments: list[AttachmentInput] = Field(default_factory=list, description="Optional attachment URLs.")
