from __future__ import annotations


class AgentError(Exception):
    """表示可直接映射为前端统一响应的业务异常。"""

    def __init__(self, status_code: int, message: str) -> None:
        """保存错误码和错误消息，供 API 层统一输出。"""
        super().__init__(message)
        self.status_code = status_code
        self.message = message
