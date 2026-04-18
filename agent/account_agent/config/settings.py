from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(slots=True)
class Settings:
    model: str
    temperature: float
    ledger_db_path: Path
    checkpoint_db_path: Path
    default_thread_id: str
    deepseek_api_key: str | None
    deepseek_base_url: str | None
    langchain_api_key: str | None
    langchain_project: str | None
    langchain_tracing_v2: bool


def _resolve_db_path(env_var: str, default_relative: str) -> Path:
    path_str = os.getenv(env_var, default_relative)
    path = Path(path_str)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path


def get_settings() -> Settings:
    ledger_db_path = _resolve_db_path("ACCOUNT_AGENT_LEDGER_DB_PATH", "./data/ledger.db")
    checkpoint_db_path = _resolve_db_path("ACCOUNT_AGENT_CHECKPOINT_DB_PATH", "./data/checkpoints.db")

    return Settings(
        model=os.getenv("ACCOUNT_AGENT_MODEL", "gpt-4.1-mini"),
        temperature=float(os.getenv("ACCOUNT_AGENT_TEMPERATURE", "0")),
        ledger_db_path=ledger_db_path,
        checkpoint_db_path=checkpoint_db_path,
        default_thread_id=os.getenv("ACCOUNT_AGENT_THREAD_ID", "demo-thread"),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL"),
        langchain_api_key=os.getenv("LANGCHAIN_API_KEY"),
        langchain_project=os.getenv("LANGCHAIN_PROJECT", "accounting-agent"),
        langchain_tracing_v2=os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true",
    )
