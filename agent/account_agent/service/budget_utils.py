from __future__ import annotations

from typing import Any

from account_agent.api.errors import AgentError


BUDGET_CYCLE_ALIASES = {
    "月": 1,
    "月度": 1,
    "monthly": 1,
    "季度": 2,
    "季": 2,
    "quarter": 2,
    "quarterly": 2,
    "年度": 3,
    "年": 3,
    "year": 3,
    "yearly": 3,
    "annual": 3,
}


def resolve_budget_cycle(
    raw_cycle: Any,
    *,
    field_name: str = "cycle",
    required: bool = True,
) -> int | None:
    """将预算周期参数统一转换为后端枚举值。"""
    if raw_cycle in (None, ""):
        if required:
            raise AgentError(status_code=400, message=f"{field_name} is required")
        return None

    if isinstance(raw_cycle, str):
        text = raw_cycle.strip()
        if text in BUDGET_CYCLE_ALIASES:
            return BUDGET_CYCLE_ALIASES[text]
        try:
            raw_cycle = int(text)
        except ValueError as exc:
            raise AgentError(status_code=400, message=f"{field_name} must be 1, 2 or 3") from exc

    try:
        cycle = int(raw_cycle)
    except (TypeError, ValueError) as exc:
        raise AgentError(status_code=400, message=f"{field_name} must be a number") from exc

    if cycle not in {1, 2, 3}:
        raise AgentError(status_code=400, message=f"{field_name} must be 1, 2 or 3")
    return cycle
