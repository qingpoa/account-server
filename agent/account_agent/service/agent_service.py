from __future__ import annotations

import json
from collections.abc import Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from account_agent.graph import create_local_agent


class AccountingAgentService:
    def __init__(self, agent=None) -> None:
        """创建一个围绕已编译 LangGraph 智能体的服务封装。"""
        self._agent = agent or create_local_agent()

    @classmethod
    def create(cls, thread_id: str | None = None) -> "AccountingAgentService":
        """创建一个带本地智能体实例的服务对象。"""
        agent = create_local_agent()
        return cls(agent=agent)

    def invoke_messages(
        self,
        messages: Sequence[BaseMessage],
        thread_id: str,
        *,
        authorization: str | None = None,
        token: str | None = None,
    ) -> dict[str, object]:
        """使用显式消息列表调用智能体。"""
        return self._agent.invoke(
            {"messages": list(messages)},
            config=self._build_graph_config(
                thread_id=thread_id,
                authorization=authorization,
                token=token,
            ),
        )

    def invoke(
        self,
        user_input: str,
        thread_id: str,
        *,
        authorization: str | None = None,
        token: str | None = None,
    ) -> dict[str, object]:
        """使用单条用户文本消息调用智能体。"""
        return self.invoke_messages(
            messages=[HumanMessage(content=user_input)],
            thread_id=thread_id,
            authorization=authorization,
            token=token,
        )

    def chat(
        self,
        user_input: str,
        thread_id: str,
        *,
        authorization: str | None = None,
        token: str | None = None,
    ) -> str:
        """返回单次用户输入对应的最终文本回复。"""
        result = self.invoke(
            user_input=user_input,
            thread_id=thread_id,
            authorization=authorization,
            token=token,
        )
        message = result["messages"][-1]
        return self._message_to_text(message.content)

    def chat_messages(
        self,
        messages: Sequence[BaseMessage],
        thread_id: str,
        *,
        authorization: str | None = None,
        token: str | None = None,
    ) -> str:
        """返回自定义消息序列对应的最终文本回复。"""
        result = self.invoke_messages(
            messages=messages,
            thread_id=thread_id,
            authorization=authorization,
            token=token,
        )
        message = result["messages"][-1]
        return self._message_to_text(message.content)

    def stream_events(
        self,
        messages: Sequence[BaseMessage],
        thread_id: str,
        *,
        authorization: str | None = None,
        token: str | None = None,
    ):
        """将图执行过程转换为前端可消费的 SSE 事件流。"""
        yield {"type": "info", "content": "盒小记 正在思考..."}
        for event in self._agent.stream(
            {"messages": list(messages)},
            config=self._build_graph_config(
                thread_id=thread_id,
                authorization=authorization,
                token=token,
            ),
            stream_mode=["updates"],
            version="v2",
        ):
            if not isinstance(event, dict) or event.get("type") != "updates":
                continue
            data = event.get("data")
            if not isinstance(data, dict):
                continue
            for node_name, payload in data.items():
                if not isinstance(payload, dict):
                    continue
                messages_payload = payload.get("messages")
                if not isinstance(messages_payload, list):
                    continue
                for message in messages_payload:
                    if isinstance(message, ToolMessage):
                        tool_input = None
                        try:
                            tool_input = json.loads(message.content)
                        except Exception:
                            tool_input = message.content
                        yield {
                            "type": "tool",
                            "name": message.name or node_name,
                            "input": tool_input,
                        }
                        continue

                    if isinstance(message, AIMessage):
                        tool_calls = getattr(message, "tool_calls", None) or []
                        for tool_call in tool_calls:
                            yield {
                                "type": "tool",
                                "name": tool_call.get("name", ""),
                                "input": tool_call.get("args", {}),
                            }
                        text = self._message_to_text(message.content)
                        if text.strip():
                            yield {"type": "delta", "content": text}
                            yield {
                                "type": "final",
                                "values": {
                                    "reply": text,
                                    "thread_id": thread_id,
                                    "node": node_name,
                                },
                            }

    def get_history(self, thread_id: str) -> dict[str, object]:
        """从图的 checkpoint 中读取指定线程的历史记录。"""
        snapshot = self._agent.get_state(
            {"configurable": {"thread_id": thread_id}},
        )
        messages = snapshot.values.get("messages", [])
        history: list[dict[str, str]] = []
        for message in messages:
            role = self._message_role(message)
            if role is None:
                continue
            history.append(
                {
                    "role": role,
                    "content": self._message_to_text(message.content),
                    "createTime": "",
                }
            )
        return {
            "thread_id": thread_id,
            "messages": history,
        }

    @staticmethod
    def _build_graph_config(
        *,
        thread_id: str,
        authorization: str | None,
        token: str | None,
    ) -> dict[str, object]:
        """构造传给 LangGraph 的 configurable 配置。"""
        configurable: dict[str, object] = {
            "thread_id": thread_id,
        }
        if authorization:
            configurable["authorization"] = authorization
        if token:
            configurable["token"] = token
        return {"configurable": configurable}

    @staticmethod
    def _message_to_text(content: object) -> str:
        """将消息内容块展开为纯文本。"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                    continue
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
            return "\n".join(part for part in parts if part).strip()
        return str(content)

    @staticmethod
    def _message_role(message: BaseMessage) -> str | None:
        """将 LangChain 消息类型映射为前端使用的角色名。"""
        if isinstance(message, HumanMessage):
            return "user"
        if isinstance(message, AIMessage):
            return "assistant"
        if isinstance(message, SystemMessage):
            return "system"
        return None
