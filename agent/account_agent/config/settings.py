from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(slots=True)
class Settings:
    model: str
    temperature: float
    request_timeout: float
    ledger_path: Path
    server_base_url: str | None
    server_auth_mode: str
    server_token: str | None
    server_timeout: float
    api_key: str | None
    base_url: str | None
    default_thread_id: str
    langchain_api_key: str | None
    langchain_project: str | None
    langchain_tracing_v2: bool


def _resolve_path(env_var: str, default_relative: str) -> Path:
    """将配置路径解析为相对于项目根目录的绝对路径。"""
    path_str = os.getenv(env_var, default_relative)
    path = Path(path_str)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """从环境变量加载并缓存运行配置。"""
    ledger_path = _resolve_path(
        "ACCOUNT_AGENT_LEDGER_PATH",
        os.getenv("ACCOUNT_AGENT_LEDGER_DB_PATH", "./data/ledger.json"),
    )

    return Settings(
        model=os.getenv("ACCOUNT_AGENT_MODEL", "qwen3.5-flash"),
        temperature=float(os.getenv("ACCOUNT_AGENT_TEMPERATURE", "0")),
        request_timeout=float(os.getenv("ACCOUNT_AGENT_REQUEST_TIMEOUT", "20")),
        ledger_path=ledger_path,
        server_base_url=os.getenv("ACCOUNT_AGENT_SERVER_BASE_URL"),
        server_auth_mode=os.getenv("ACCOUNT_AGENT_SERVER_AUTH_MODE", "bearer").strip().lower(),
        server_token=os.getenv("ACCOUNT_AGENT_SERVER_TOKEN"),
        server_timeout=float(os.getenv("ACCOUNT_AGENT_SERVER_TIMEOUT", "20")),
        api_key=os.getenv("ACCOUNT_AGENT_API_KEY") or os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("ACCOUNT_AGENT_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL"),
        default_thread_id=os.getenv("ACCOUNT_AGENT_THREAD_ID", "demo-thread"),
        langchain_api_key=os.getenv("LANGCHAIN_API_KEY"),
        langchain_project=os.getenv("LANGCHAIN_PROJECT", "accounting-agent"),
        langchain_tracing_v2=os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true",
    )
