from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from market_analyst.types.supervisor import SupervisorAnalysisResult


ChatRole = Literal["user", "assistant"]


@dataclass(frozen=True)
class SupervisorChatContext:
    company_name: str
    ticker: str
    sector: str | None = None
    supervisor_result: SupervisorAnalysisResult | None = None


@dataclass(frozen=True)
class SupervisorChatMessage:
    role: ChatRole
    content: str


@dataclass(frozen=True)
class SupervisorChatRequest:
    context: SupervisorChatContext
    message: str
    history: list[SupervisorChatMessage] = field(default_factory=list)
    max_history_messages: int = 12


@dataclass(frozen=True)
class SupervisorChatResponse:
    answer: str
    history: list[SupervisorChatMessage]
    tool_names: list[str] = field(default_factory=list)
