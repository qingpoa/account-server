from __future__ import annotations

from collections.abc import Mapping

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

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


def _build_model(model=None):
    settings = get_settings()
    default_kwargs = {
        "model": settings.model,
        "temperature": settings.temperature,
        "api_key": settings.deepseek_api_key,
        "base_url": settings.deepseek_base_url or "https://api.deepseek.com",
    }

    if model is None:
        return ChatOpenAI(**default_kwargs)

    if hasattr(model, "bind_tools"):
        return model

    if isinstance(model, Mapping):
        model_kwargs = dict(default_kwargs)
        model_name = model.get("model") or model.get("name")
        if model_name:
            model_kwargs["model"] = model_name
        if "temperature" in model:
            model_kwargs["temperature"] = model["temperature"]
        if model.get("base_url"):
            model_kwargs["base_url"] = model["base_url"]
        if model.get("api_key"):
            model_kwargs["api_key"] = model["api_key"]
        return ChatOpenAI(**model_kwargs)

    raise TypeError(f"Unsupported model value: {type(model).__name__}")


def create_agent(model=None, checkpointer=None):
    tools = get_tools()
    llm_with_tools = _build_model(model=model).bind_tools(tools)

    def assistant(state: MessagesState) -> dict[str, list]:
        response = llm_with_tools.invoke(
            [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        )
        return {"messages": [response]}

    def route_after_assistant(state: MessagesState):
        last_message = state["messages"][-1]
        if getattr(last_message, "tool_calls", None):
            return "tools"
        return END

    graph = StateGraph(MessagesState)
    graph.add_node("assistant", assistant)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "assistant")
    graph.add_conditional_edges(
        "assistant",
        route_after_assistant,
        {"tools": "tools", END: END},
    )
    graph.add_edge("tools", "assistant")

    if checkpointer is not None and hasattr(checkpointer, "setup"):
        checkpointer.setup()

    return graph.compile(checkpointer=checkpointer)


def create_local_agent(model=None):
    return create_agent(model=model, checkpointer=InMemorySaver())


def build_graph(model=None):
    return create_agent(model=model)
