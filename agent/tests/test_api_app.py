from __future__ import annotations

import unittest

from langchain_core.messages import HumanMessage

try:
    from fastapi.testclient import TestClient

    from account_agent.api.app import create_app
    from account_agent.api.errors import AgentError

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    TestClient = None
    create_app = None
    AgentError = Exception


class StubAgentService:
    def __init__(self) -> None:
        """为 API 测试准备一个简单的智能体桩对象。"""
        self.last_chat: dict[str, object] | None = None
        self.last_chat_messages: dict[str, object] | None = None
        self.last_stream_messages: dict[str, object] | None = None

    def chat(self, user_input: str, thread_id: str) -> str:
        """模拟阻塞式文本对话入口。"""
        self.last_chat = {
            "user_input": user_input,
            "thread_id": thread_id,
        }
        return "text reply"

    def chat_messages(self, messages, thread_id: str) -> str:
        """模拟多模态阻塞式对话入口。"""
        self.last_chat_messages = {
            "messages": messages,
            "thread_id": thread_id,
        }
        return "image reply"

    def stream_events(self, messages, thread_id: str):
        """模拟智能体返回的 SSE 事件流。"""
        self.last_stream_messages = {
            "messages": messages,
            "thread_id": thread_id,
        }
        yield {"type": "info", "content": "Agent 正在思考..."}
        yield {"type": "tool", "name": "add_bill", "input": {"amount": 20}}
        yield {"type": "delta", "content": "已为你记下一笔支出。"}
        yield {"type": "final", "values": {"reply": "已为你记下一笔支出。", "thread_id": thread_id}}

    def get_history(self, thread_id: str) -> dict[str, object]:
        """返回固定的线程历史数据供测试使用。"""
        return {
            "thread_id": thread_id,
            "messages": [
                {"role": "user", "content": "工资发了2000", "createTime": ""},
                {"role": "assistant", "content": "已为你记下一笔收入。", "createTime": ""},
            ],
        }


class FailingAgentService(StubAgentService):
    """用于验证统一异常出口的失败桩对象。"""

    def chat(self, user_input: str, thread_id: str) -> str:
        """模拟阻塞式接口抛出业务异常。"""
        raise AgentError(status_code=503, message="大模型服务调用失败")

    def stream_events(self, messages, thread_id: str):
        """模拟流式接口执行过程中抛出异常。"""
        raise RuntimeError("stream exploded")


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed in the current environment")
class ApiAppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        """创建一个由桩智能体驱动的测试客户端。"""
        self.service = StubAgentService()
        self.client = TestClient(create_app(agent_service=self.service))

    def test_health_success(self) -> None:
        """健康检查接口应返回正常结果。"""
        response = self.client.get("/api/v1/health")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["data"]["status"], "ok")

    def test_text_chat_success(self) -> None:
        """阻塞式文本对话应正确转发到智能体服务。"""
        response = self.client.post(
            "/api/v1/agent/chat",
            json={"message": "工资发了2000", "thread_id": "thread-api-text"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["data"]["reply"], "text reply")
        self.assertEqual(self.service.last_chat["user_input"], "工资发了2000")
        self.assertEqual(self.service.last_chat["thread_id"], "thread-api-text")

    def test_stream_chat_success(self) -> None:
        """流式对话应返回预期的 SSE 事件类型。"""
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
        """非流式模式应退回普通 JSON 响应。"""
        response = self.client.post(
            "/api/v1/chat/stream",
            json={"message": "工资发了2000", "thread_id": "thread-stream", "stream": False},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["data"]["thread_id"], "thread-stream")

    def test_stream_chat_with_image_url_success(self) -> None:
        """图片附件应转换为 image_url 消息块。"""
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
        """不支持的附件类型应直接返回 400。"""
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
        body = response.json()
        self.assertEqual(body["code"], 400)
        self.assertIn("Unsupported attachment type", body["msg"])

    def test_chat_history_success(self) -> None:
        """历史接口应正确代理线程历史记录。"""
        response = self.client.get("/api/v1/chat/history/thread-history")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["data"]["thread_id"], "thread-history")
        self.assertEqual(len(body["data"]["messages"]), 2)

    def test_validation_error_is_mapped_to_400(self) -> None:
        """参数校验失败时应统一映射为 400 结构。"""
        response = self.client.post(
            "/api/v1/chat/stream",
            json={"message": "", "thread_id": "thread-stream", "stream": False},
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["code"], 400)
        self.assertIsNone(body["data"])
        self.assertTrue(body["msg"])

    def test_agent_error_uses_same_error_shape(self) -> None:
        """业务异常应输出和 Java 后端一致的错误结构。"""
        client = TestClient(create_app(agent_service=FailingAgentService()))
        response = client.post(
            "/api/v1/agent/chat",
            json={"message": "工资发了2000", "thread_id": "thread-api-text"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "code": 503,
                "msg": "大模型服务调用失败",
                "data": None,
            },
        )

    def test_stream_error_event_uses_unified_code_and_message(self) -> None:
        """流式执行失败时应发出统一的 error 事件。"""
        client = TestClient(create_app(agent_service=FailingAgentService()))
        response = client.post(
            "/api/v1/chat/stream",
            json={"message": "工资发了2000", "thread_id": "thread-stream", "stream": True},
        )

        self.assertEqual(response.status_code, 200)
        text = response.text
        self.assertIn('"type": "error"', text)
        self.assertIn('"code": 500', text)
        self.assertIn('"msg": "stream exploded"', text)
        self.assertIn("[DONE]", text)
