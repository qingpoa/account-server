from .analysis_tools import get_analysis_tools
from .budget_tools import (
    get_budget_command_service,
    get_budget_query_service,
    get_budget_tools,
)
from .ledger_tools import (
    get_bill_command_service,
    get_bill_query_service,
    get_ledger_tools,
    get_stat_query_service,
)


def get_tools() -> list:
    """返回默认暴露给主智能体的全部工具集合。"""
    return [*get_ledger_tools(), *get_budget_tools()]

__all__ = [
    "get_analysis_tools",
    "get_bill_command_service",
    "get_bill_query_service",
    "get_budget_command_service",
    "get_budget_query_service",
    "get_budget_tools",
    "get_ledger_tools",
    "get_stat_query_service",
    "get_tools",
]
