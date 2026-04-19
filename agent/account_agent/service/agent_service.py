from __future__ import annotations

from collections.abc import Sequence

from langchain_core.messages import BaseMessage, HumanMessage

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
