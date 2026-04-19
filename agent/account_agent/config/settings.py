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
    ledger_path: Path
    api_key: str | None
    base_url: str | None
    vision_model: str | None
    vision_api_key: str | None
    vision_base_url: str | None
    default_thread_id: str
    deepseek_api_key: str | None
    deepseek_base_url: str | None
    langchain_api_key: str | None
    langchain_project: str | None
    langchain_tracing_v2: bool


def _resolve_path(env_var: str, default_relative: str) -> Path:
    path_str = os.getenv(env_var, default_relative)
    path = Path(path_str)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    ledger_path = _resolve_path(
        "ACCOUNT_AGENT_LEDGER_PATH",
        os.getenv("ACCOUNT_AGENT_LEDGER_DB_PATH", "./data/ledger.json"),
    )

    return Settings(
        model=os.getenv("ACCOUNT_AGENT_MODEL", "qwen3.5-flash"),
        temperature=float(os.getenv("ACCOUNT_AGENT_TEMPERATURE", "0")),
        ledger_path=ledger_path,
        api_key=os.getenv("ACCOUNT_AGENT_API_KEY") or os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("ACCOUNT_AGENT_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL"),
        vision_model=os.getenv("ACCOUNT_AGENT_VISION_MODEL", "qwen3.5-flash"),
        vision_api_key=(
            os.getenv("ACCOUNT_AGENT_VISION_API_KEY")
            or os.getenv("ACCOUNT_AGENT_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
        ),
        vision_base_url=(
            os.getenv("ACCOUNT_AGENT_VISION_BASE_URL")
            or os.getenv("ACCOUNT_AGENT_BASE_URL")
            or os.getenv("DEEPSEEK_BASE_URL")
        ),
        default_thread_id=os.getenv("ACCOUNT_AGENT_THREAD_ID", "demo-thread"),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL"),
        langchain_api_key=os.getenv("LANGCHAIN_API_KEY"),
        langchain_project=os.getenv("LANGCHAIN_PROJECT", "accounting-agent"),
        langchain_tracing_v2=os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true",
    )
