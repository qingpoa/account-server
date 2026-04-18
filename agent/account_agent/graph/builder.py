from __future__ import annotations

import sqlite3

from langchain.agents import create_agent as _langchain_create_agent
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver

from account_agent.config import get_settings
from account_agent.tools import get_tools


SYSTEM_PROMPT = """
你是一个记账系统智能体。

必须遵守下面的规则：
1. 用户要求新增账单时，优先调用工具，不要只做口头回复。
2. 金额统一使用正数。
3. `kind` 只允许 `expense` 或 `income`。
4. 分类尽量规范，优先使用：餐饮、交通、购物、工资、住房、其他。
5. 查询和统计时，优先基于工具真实结果回答，再补一句简洁总结。
6. 如果用户信息不足，先根据上下文补齐最必要字段；仍然不够时再简洁追问。
7. 不要编造账单或统计结果。
""".strip()


def create_agent(model=None, checkpointer=None):
    settings = get_settings()
    llm = model or ChatOpenAI(
        model=settings.model,
        temperature=settings.temperature,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url or "https://api.deepseek.com",
    )
    checkpointer = checkpointer or SqliteSaver(conn=sqlite3.connect(str(settings.checkpoint_db_path), check_same_thread=False))
    checkpointer.setup()
    return _langchain_create_agent(
        model=llm,
        tools=get_tools(),
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )


def build_graph(model=None):
    return create_agent(model=model)
