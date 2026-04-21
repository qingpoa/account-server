from __future__ import annotations

import unittest

from langchain_core.messages import HumanMessage

try:
    from fastapi.testclient import TestClient

    from account_agent.api.app import create_app

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    TestClient = None
    create_app = None


class StubAgentService:
    def __init__(self) -> None:
        self.last_chat: dict[str, object] | None = None
        self.last_chat_messages: dict[str, object] | None = None
        self.last_stream_messages: dict[str, object] | None = None

    def chat(self, user_input: str, thread_id: str) -> str:
        self.last_chat = {
            "user_input": user_input,
            "thread_id": thread_id,
        }
        return "text reply"

    def chat_messages(self, messages, thread_id: str) -> str:
        self.last_chat_messages = {
            "messages": messages,
            "thread_id": thread_id,
        }
        return "image reply"

    def stream_events(self, messages, thread_id: str):
        self.last_stream_messages = {
            "messages": messages,
            "thread_id": thread_id,
        }
        yield {"type": "info", "content": "Agent 正在思考..."}
        yield {"type": "tool", "name": "add_bill", "input": {"amount": 20}}
        yield {"type": "delta", "content": "已为你记下一笔支出。"}
        yield {"type": "final", "values": {"reply": "已为你记下一笔支出。", "thread_id": thread_id}}

    def get_history(self, thread_id: str) -> dict[str, object]:
        return {
            "thread_id": thread_id,
            "messages": [
                {"role": "user", "content": "工资发了2000", "createTime": ""},
                {"role": "assistant", "content": "已为你记下一笔收入。", "createTime": ""},
            ],
        }


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed in the current environment")
class ApiAppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.service = StubAgentService()
        self.client = TestClient(create_app(agent_service=self.service))

    def test_health_success(self) -> None:
        response = self.client.get("/api/v1/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_text_chat_success(self) -> None:
        response = self.client.post(
            "/api/v1/agent/chat",
            json={"message": "工资发了2000", "thread_id": "thread-api-text"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], "text reply")
        self.assertEqual(self.service.last_chat["user_input"], "工资发了2000")
        self.assertEqual(self.service.last_chat["thread_id"], "thread-api-text")

    def test_stream_chat_success(self) -> None:
        response = self.client.post(
            "/api/v1/chat/stream",
            json={"message": "工资发了2000", "thread_id": "thread-stream", "stream": True},
        )

        self.assertEqual(response.status_code, 200)
        text = response.text
        self.assertIn('"type": "info"', text)
        self.assertIn('"type": "tool"', text)
        self.assertIn('"type": "delta"', text)
        self.assertIn("[DONE]", text)

    def test_stream_chat_non_stream_mode_returns_json(self) -> None:
        response = self.client.post(
            "/api/v1/chat/stream",
            json={"message": "工资发了2000", "thread_id": "thread-stream", "stream": False},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["data"]["thread_id"], "thread-stream")

    def test_stream_chat_with_image_url_success(self) -> None:
        response = self.client.post(
            "/api/v1/chat/stream",
            json={
                "message": "识别这张图片并记账",
                "thread_id": "thread-stream-image",
                "stream": False,
                "attachments": [
                    {
                        "type": "image",
                        "url": "https://oss.example.com/account/receipt.jpg",
                    }
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = self.service.last_chat_messages
        self.assertEqual(payload["thread_id"], "thread-stream-image")
        self.assertEqual(len(payload["messages"]), 1)
        self.assertIsInstance(payload["messages"][0], HumanMessage)
        content = payload["messages"][0].content
        self.assertEqual(content[0]["type"], "text")
        self.assertEqual(content[1]["type"], "image_url")
        self.assertEqual(
            content[1]["image_url"]["url"],
            "https://oss.example.com/account/receipt.jpg",
        )

    def test_stream_chat_rejects_unsupported_attachment_type(self) -> None:
        response = self.client.post(
            "/api/v1/chat/stream",
            json={
                "message": "识别附件",
                "thread_id": "thread-stream-file",
                "stream": False,
                "attachments": [
                    {
                        "type": "pdf",
                        "url": "https://oss.example.com/account/report.pdf",
                    }
                ],
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported attachment type", response.json()["detail"])

    def test_chat_history_success(self) -> None:
        response = self.client.get("/api/v1/chat/history/thread-history")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["data"]["thread_id"], "thread-history")
        self.assertEqual(len(body["data"]["messages"]), 2)
