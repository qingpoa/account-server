from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthData(BaseModel):
    """描述健康检查接口 data 字段中的载荷结构。"""

    ok: bool = True
    status: str = "ok"


class HealthResponse(BaseModel):
    """描述统一健康检查响应结构。"""

    code: int = 200
    msg: str = "success"
    data: HealthData = Field(default_factory=HealthData)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="用户输入的文本消息。")
    thread_id: str | None = Field(default=None, description="对话线程 ID。")


class ChatData(BaseModel):
    """描述阻塞式聊天接口 data 字段中的载荷结构。"""

    thread_id: str = Field(description="对话线程 ID。")
    reply: str = Field(description="智能体最终回复文本。")


class ChatResponse(BaseModel):
    """描述统一聊天响应结构。"""

    code: int = 200
    msg: str = "success"
    data: ChatData


class AttachmentInput(BaseModel):
    type: str = Field(default="image", description="附件类型，当前仅支持 image。")
    url: str = Field(min_length=1, description="可直接访问的附件地址。")


class ChatStreamRequest(BaseModel):
    message: str = Field(min_length=1, description="用户输入内容。")
    thread_id: str = Field(min_length=1, description="对话线程 ID。")
    stream: bool = Field(default=True, description="是否启用 SSE 流式输出。")
    metadata: dict[str, Any] | None = Field(default=None, description="可选的上下文元数据。")
    attachments: list[AttachmentInput] = Field(default_factory=list, description="可选的附件地址列表。")
