from __future__ import annotations

import json
from collections.abc import Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from account_agent.graph import create_local_agent


class AccountingAgentService:
    def __init__(self, agent=None) -> None:
        self._agent = agent or create_local_agent()

    @classmethod
    def create(cls, thread_id: str | None = None) -> "AccountingAgentService":
        agent = create_local_agent()
        return cls(agent=agent)

    def invoke_messages(
        self,
        messages: Sequence[BaseMessage],
        thread_id: str,
    ) -> dict[str, object]:
        return self._agent.invoke(
            {"messages": list(messages)},
            config={"configurable": {"thread_id": thread_id}},
        )

    def invoke(self, user_input: str, thread_id: str) -> dict[str, object]:
        return self.invoke_messages(
            messages=[HumanMessage(content=user_input)],
            thread_id=thread_id,
        )

    def chat(self, user_input: str, thread_id: str) -> str:
        result = self.invoke(user_input=user_input, thread_id=thread_id)
        message = result["messages"][-1]
        return self._message_to_text(message.content)

    def chat_messages(
        self,
        messages: Sequence[BaseMessage],
        thread_id: str,
    ) -> str:
        result = self.invoke_messages(messages=messages, thread_id=thread_id)
        message = result["messages"][-1]
        return self._message_to_text(message.content)

    def stream_events(
        self,
        messages: Sequence[BaseMessage],
        thread_id: str,
    ):
        yield {"type": "info", "content": "Agent 正在思考..."}
        for event in self._agent.stream(
            {"messages": list(messages)},
            config={"configurable": {"thread_id": thread_id}},
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
    def _message_to_text(content: object) -> str:
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
        if isinstance(message, HumanMessage):
            return "user"
        if isinstance(message, AIMessage):
            return "assistant"
        if isinstance(message, SystemMessage):
            return "system"
        return None
