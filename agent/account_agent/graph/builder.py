from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from uuid import uuid4

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from account_agent.config import get_settings
from account_agent.service import ImageAnalysisService
from account_agent.service.analysis_models import ImageAnalysisResult
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
    """根据配置或传入覆盖值构建基础对话模型。"""
    settings = get_settings()
    default_kwargs = {
        "model": settings.model,
        "temperature": settings.temperature,
        "timeout": settings.request_timeout,
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
    """返回当前图状态中的最后一条用户消息。"""
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            return message
    return None


def _human_input_parts(message: HumanMessage | None) -> tuple[str, list[dict[str, object]]]:
    """将用户消息拆成纯文本和图片内容块。"""
    if message is None:
        return "", []

    content = message.content
    if isinstance(content, str):
        return content.strip(), []
    if not isinstance(content, Sequence):
        return str(content), []

    text_parts: list[str] = []
    image_blocks: list[dict[str, object]] = []
    for block in content:
        if isinstance(block, str):
            text_parts.append(block)
        elif isinstance(block, Mapping):
            block_type = str(block.get("type", "")).lower()
            if block_type == "text":
                text_parts.append(str(block.get("text", "")))
            elif block_type in {"image", "image_url"}:
                image_blocks.append(dict(block))
    return "\n".join(part for part in text_parts if part).strip(), image_blocks


def _tool_payload(message: AnyMessage) -> dict[str, object]:
    """将工具结果消息解析为字典载荷。"""
    content = message.content
    if isinstance(content, Mapping):
        return dict(content)
    if isinstance(content, str):
        return json.loads(content)
    if isinstance(content, list):
        text = "\n".join(
            str(block.get("text", ""))
            for block in content
            if isinstance(block, Mapping) and block.get("type") == "text"
        ).strip()
        if text:
            return json.loads(text)
    raise ValueError("工具结果不是合法 JSON")


def create_agent(model=None, checkpointer=None, analysis_service: ImageAnalysisService | None = None):
    """创建并编译记账智能体的 LangGraph 工作流。"""
    ledger_tools = get_tools()
    base_llm = _build_model(model=model)
    assistant_llm = base_llm.bind_tools(ledger_tools)
    analysis_tools = get_analysis_tools(
        analysis_service or ImageAnalysisService(llm=base_llm if model is not None else None)
    )

    def classify_input(state: AccountAgentState) -> dict[str, object]:
        """在收到新的图片请求时重置待补全账单状态。"""
        _, image_blocks = _human_input_parts(_last_human_message(state))
        if image_blocks:
            return {"pending_bill_candidate": None}
        return {}

    def route_after_classify(state: AccountAgentState):
        """将请求路由到图片分支或文本分支。"""
        _, image_blocks = _human_input_parts(_last_human_message(state))
        if image_blocks:
            return "analyze_image"
        return "assistant"

    def analyze_image(state: AccountAgentState) -> dict[str, list[AIMessage]]:
        """构造一个调用图片分析工具的工具请求。"""
        message = _last_human_message(state)
        user_text, image_blocks = _human_input_parts(message)
        tool_call = {
            "name": "analyze_accounting_image",
            "args": {
                "user_text": user_text,
                "image_blocks": image_blocks,
            },
            "id": f"call_{uuid4().hex}",
            "type": "tool_call",
        }
        return {"messages": [AIMessage(content="", tool_calls=[tool_call])]}

    def handle_image_analysis(state: AccountAgentState) -> dict[str, object]:
        """根据图片分析结果生成追问回复或新增账单工具调用。"""
        analysis = ImageAnalysisResult.model_validate(_tool_payload(state["messages"][-1]))
        if not analysis.is_accounting_related:
            content = "这张图片和记账无关，我先不为它记账。"
            if analysis.raw_summary:
                content = f"{content} {analysis.raw_summary}"
            return {
                "messages": [AIMessage(content=content)],
                "pending_bill_candidate": None,
            }

        if analysis.bill_candidate and not analysis.missing_fields:
            tool_call = {
                "name": "add_bill",
                "args": analysis.bill_candidate.model_dump(),
                "id": f"call_{uuid4().hex}",
                "type": "tool_call",
            }
            return {
                "messages": [AIMessage(content="", tool_calls=[tool_call])],
                "pending_bill_candidate": analysis.bill_candidate.model_dump(),
            }

        labels = [MISSING_FIELD_LABELS.get(field, field) for field in analysis.missing_fields] or ["金额", "收支类型", "分类"]
        content = f"这张图片和记账有关，还缺少：{'、'.join(labels)}。请直接补充缺失信息，我再为你记账。"
        if analysis.raw_summary:
            content = f"{analysis.raw_summary}\n{content}"
        return {
            "messages": [AIMessage(content=content)],
            "pending_bill_candidate": analysis.bill_candidate.model_dump() if analysis.bill_candidate else None,
        }

    def assistant(state: AccountAgentState) -> dict[str, object]:
        """运行绑定了账本工具的主助手模型。"""
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        candidate = state.get("pending_bill_candidate")
        if candidate:
            messages.append(
                SystemMessage(
                    content=(
                        "当前有一笔待补全的图片账单候选："
                        f"{json.dumps(candidate, ensure_ascii=False)}。"
                        "优先根据用户最新回复补齐并在关键字段完整后调用 add_bill。"
                    )
                )
            )
        messages.extend(state["messages"])
        response = assistant_llm.invoke(
            messages
        )
        return {"messages": [response]}

    def route_after_assistant(state: AccountAgentState):
        """将助手产生的工具调用路由到工具节点，否则结束流程。"""
        if getattr(state["messages"][-1], "tool_calls", None):
            return "ledger_tools"
        return END

    def route_after_ledger(state: AccountAgentState):
        """判断账本工具结果是直接生成回执还是继续交给助手处理。"""
        payload = _tool_payload(state["messages"][-1])
        if isinstance(payload.get("bill"), Mapping):
            return "bill_reply_assistant"
        return "assistant"

    def bill_reply_assistant(state: AccountAgentState) -> dict[str, object]:
        """在成功记账后生成简短自然语言确认回复。"""
        payload = _tool_payload(state["messages"][-1])
        bill = payload.get("bill") if isinstance(payload.get("bill"), Mapping) else {}
        fallback = "已帮你完成记账。"
        if bill:
            details = []
            if bill.get("kind") == "income":
                details.append("收入")
            elif bill.get("kind") == "expense":
                details.append("支出")
            if bill.get("amount") is not None:
                details.append(f"{bill.get('amount')} 元")
            if bill.get("category"):
                details.append(f"分类 {bill.get('category')}")
            if bill.get("occurred_at"):
                details.append(f"时间 {bill.get('occurred_at')}")
            if bill.get("note"):
                details.append(f"备注 {bill.get('note')}")
            if details:
                fallback = f"已帮你记账：{'，'.join(str(item) for item in details)}。"
        try:
            response = base_llm.invoke(
                [
                    SystemMessage(
                        content=(
                            "你是记账系统的回执助手。"
                            "请严格基于工具真实结果，用自然、简洁的中文回复用户。"
                            "不要编造，不要再次调用工具，控制在 1 到 2 句。"
                        )
                    ),
                    HumanMessage(
                        content=(
                            "请基于下面的工具真实结果，生成一条面向用户的记账确认回复：\n"
                            f"{json.dumps(payload, ensure_ascii=False)}"
                        )
                    ),
                ]
            )
            text = response.text.strip() if hasattr(response, "text") else str(response.content).strip()
        except Exception:
            text = ""
        return {
            "messages": [AIMessage(content=text or fallback)],
            "pending_bill_candidate": None,
        }

    graph = StateGraph(AccountAgentState)
    graph.add_node("classify_input", classify_input)
    graph.add_node("analyze_image", analyze_image)
    graph.add_node("analysis_tools", ToolNode(analysis_tools))
    graph.add_node("handle_image_analysis", handle_image_analysis)
    graph.add_node("assistant", assistant)
    graph.add_node("ledger_tools", ToolNode(ledger_tools))
    graph.add_node("bill_reply_assistant", bill_reply_assistant)

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
        {"bill_reply_assistant": "bill_reply_assistant", "assistant": "assistant"},
    )
    graph.add_edge("bill_reply_assistant", END)

    if checkpointer is not None and hasattr(checkpointer, "setup"):
        checkpointer.setup()

    return graph.compile(checkpointer=checkpointer)


def create_local_agent(model=None, analysis_service: ImageAnalysisService | None = None):
    """创建一个使用内存 checkpoint 的本地智能体。"""
    return create_agent(model=model, checkpointer=InMemorySaver(), analysis_service=analysis_service)


def build_graph(model=None):
    """构建可部署的图，不强制绑定本地 checkpoint。"""
    return create_agent(model=model)
