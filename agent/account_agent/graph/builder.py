from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from account_agent.config import get_settings
from account_agent.service import ImageAnalysisService
from account_agent.tools import get_analysis_tools, get_tools


SYSTEM_PROMPT = """
你是一个记账系统智能体。

必须遵守下面的规则：
1. 用户要求新增账单时，优先调用工具，不要只做口头回复。
2. 金额统一使用正数。
3. `kind` 只允许 `expense` 或 `income`。
4. 分类尽量规范，优先使用：餐饮、交通、购物、工资、住房、其他。
5. 查询和统计时，优先基于工具真实结果回答，再补一句简洁总结。
6. 不要编造账单或统计结果。
7. 当上下文里有一笔待补全的图片账单时，优先补齐它；只有 `amount`、`kind`、`category` 都齐全后才调用 `add_bill`。
""".strip()

MISSING_FIELD_LABELS = {
    "amount": "金额",
    "kind": "收支类型",
    "category": "分类",
}


class AccountAgentState(MessagesState, total=False):
    pending_bill_candidate: dict[str, object] | None


def _build_model(model=None):
    settings = get_settings()
    default_kwargs = {
        "model": settings.model,
        "temperature": settings.temperature,
        "api_key": settings.api_key,
        "base_url": settings.base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
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


def _last_human_message(state: AccountAgentState) -> HumanMessage | None:
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            return message
    return None


def _message_to_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, Mapping) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "\n".join(part for part in parts if part).strip()
    return str(content)


def _extract_image_blocks(message: HumanMessage | None) -> list[dict[str, object]]:
    if message is None:
        return []

    content = message.content
    if not isinstance(content, Sequence) or isinstance(content, str):
        return []

    return [
        dict(block)
        for block in content
        if isinstance(block, Mapping) and str(block.get("type", "")).lower() in {"image", "image_url"}
    ]


def _parse_tool_payload(content: object) -> dict[str, object]:
    if isinstance(content, Mapping):
        return dict(content)
    return json.loads(_message_to_text(content))


def _candidate_to_bill_args(candidate: Mapping[str, object]) -> dict[str, object]:
    return {
        "amount": candidate["amount"],
        "kind": candidate["kind"],
        "category": candidate["category"],
        "note": str(candidate.get("note") or ""),
        "occurred_at": candidate.get("occurred_at"),
    }


def _format_missing_fields_message(analysis_result: Mapping[str, object]) -> str:
    missing_fields = analysis_result.get("missing_fields")
    if not isinstance(missing_fields, Sequence) or isinstance(missing_fields, (str, bytes)):
        missing_fields = []
    labels = [MISSING_FIELD_LABELS.get(str(field), str(field)) for field in missing_fields] or [
        "金额",
        "收支类型",
        "分类",
    ]
    summary = str(analysis_result.get("raw_summary") or "").strip()
    prefix = f"这张图片和记账有关。{summary}" if summary else "这张图片和记账有关。"
    return f"{prefix}\n还缺少：{'、'.join(labels)}。请直接补充缺失信息，我再为你记账。"


def _format_irrelevant_image_message(analysis_result: Mapping[str, object]) -> str:
    summary = str(analysis_result.get("raw_summary") or "").strip()
    if summary:
        return f"这张图片和记账无关，我先不为它记账。识别摘要：{summary}"
    return "这张图片和记账无关，我先不为它记账。"


def _format_image_add_success(tool_payload: Mapping[str, object]) -> str:
    bill = tool_payload.get("bill")
    if not isinstance(bill, Mapping):
        return "已根据图片内容完成记账。"
    return (
        "已根据图片内容记账成功："
        f"{bill.get('kind')} {bill.get('amount')} 元，"
        f"分类 {bill.get('category')}，"
        f"时间 {bill.get('occurred_at')}。"
    )


def _assistant_context(state: AccountAgentState) -> list[SystemMessage]:
    candidate = state.get("pending_bill_candidate")
    if not candidate:
        return []
    return [
        SystemMessage(
            content=(
                "当前有一笔待补全的图片账单候选："
                f"{json.dumps(candidate, ensure_ascii=False)}。"
                "优先根据用户最新回复补齐并在关键字段完整后调用 add_bill。"
            )
        )
    ]


def create_agent(model=None, checkpointer=None, analysis_service: ImageAnalysisService | None = None):
    ledger_tools = get_tools()
    base_llm = _build_model(model=model)
    assistant_llm = base_llm.bind_tools(ledger_tools)
    analysis_tools = get_analysis_tools(
        analysis_service or ImageAnalysisService(llm=base_llm if model is not None else None)
    )

    def classify_input(state: AccountAgentState) -> dict[str, object]:
        if _extract_image_blocks(_last_human_message(state)):
            return {"pending_bill_candidate": None}
        return {}

    def route_after_classify(state: AccountAgentState):
        if _extract_image_blocks(_last_human_message(state)):
            return "analyze_image"
        return "assistant"

    def analyze_image(state: AccountAgentState) -> dict[str, list[AIMessage]]:
        message = _last_human_message(state)
        tool_call = {
            "name": "analyze_accounting_image",
            "args": {
                "user_text": _message_to_text(message.content if message else ""),
                "image_blocks": _extract_image_blocks(message),
            },
            "id": f"call_{uuid4().hex}",
            "type": "tool_call",
        }
        return {"messages": [AIMessage(content="", tool_calls=[tool_call])]}

    def handle_image_analysis(state: AccountAgentState) -> dict[str, object]:
        payload = _parse_tool_payload(state["messages"][-1].content)
        if not payload.get("is_accounting_related"):
            return {
                "messages": [AIMessage(content=_format_irrelevant_image_message(payload))],
                "pending_bill_candidate": None,
            }

        candidate = payload.get("bill_candidate")
        if isinstance(candidate, Mapping) and not payload.get("missing_fields"):
            tool_call = {
                "name": "add_bill",
                "args": _candidate_to_bill_args(candidate),
                "id": f"call_{uuid4().hex}",
                "type": "tool_call",
            }
            return {
                "messages": [AIMessage(content="", tool_calls=[tool_call])],
                "pending_bill_candidate": dict(candidate),
            }

        return {
            "messages": [AIMessage(content=_format_missing_fields_message(payload))],
            "pending_bill_candidate": dict(candidate) if isinstance(candidate, Mapping) else None,
        }

    def assistant(state: AccountAgentState) -> dict[str, object]:
        response = assistant_llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                *_assistant_context(state),
                *state["messages"],
            ]
        )
        return {"messages": [response]}

    def route_after_assistant(state: AccountAgentState):
        if getattr(state["messages"][-1], "tool_calls", None):
            return "ledger_tools"
        return END

    def route_after_ledger(state: AccountAgentState):
        if state.get("pending_bill_candidate"):
            return "finalize_image_bill"
        return "assistant"

    def finalize_image_bill(state: AccountAgentState) -> dict[str, object]:
        payload = _parse_tool_payload(state["messages"][-1].content)
        return {
            "messages": [AIMessage(content=_format_image_add_success(payload))],
            "pending_bill_candidate": None,
        }

    graph = StateGraph(AccountAgentState)
    graph.add_node("classify_input", classify_input)
    graph.add_node("analyze_image", analyze_image)
    graph.add_node("analysis_tools", ToolNode(analysis_tools))
    graph.add_node("handle_image_analysis", handle_image_analysis)
    graph.add_node("assistant", assistant)
    graph.add_node("ledger_tools", ToolNode(ledger_tools))
    graph.add_node("finalize_image_bill", finalize_image_bill)

    graph.add_edge(START, "classify_input")
    graph.add_conditional_edges(
        "classify_input",
        route_after_classify,
        {"analyze_image": "analyze_image", "assistant": "assistant"},
    )
    graph.add_edge("analyze_image", "analysis_tools")
    graph.add_edge("analysis_tools", "handle_image_analysis")
    graph.add_conditional_edges(
        "handle_image_analysis",
        route_after_assistant,
        {"ledger_tools": "ledger_tools", END: END},
    )
    graph.add_conditional_edges(
        "assistant",
        route_after_assistant,
        {"ledger_tools": "ledger_tools", END: END},
    )
    graph.add_conditional_edges(
        "ledger_tools",
        route_after_ledger,
        {"finalize_image_bill": "finalize_image_bill", "assistant": "assistant"},
    )
    graph.add_edge("finalize_image_bill", END)

    if checkpointer is not None and hasattr(checkpointer, "setup"):
        checkpointer.setup()

    return graph.compile(checkpointer=checkpointer)


def create_local_agent(model=None, analysis_service: ImageAnalysisService | None = None):
    return create_agent(model=model, checkpointer=InMemorySaver(), analysis_service=analysis_service)


def build_graph(model=None):
    return create_agent(model=model)
