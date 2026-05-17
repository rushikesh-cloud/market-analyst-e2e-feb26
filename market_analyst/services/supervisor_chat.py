from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain.agents import create_agent
from langchain_core.tools import BaseTool, tool

from market_analyst.config.settings import Settings
from market_analyst.services.agent import build_chat_model
from market_analyst.services.agents.fundamental import run_fundamental_analysis_agent
from market_analyst.services.agents.news import run_news_analysis_agent
from market_analyst.services.agents.technical import run_technical_analysis_agent
from market_analyst.telemetry import invoke_agent_with_tracing
from market_analyst.types.fundamental import FundamentalAnalysisRequest, FundamentalAnalysisResult
from market_analyst.types.news import NewsAnalysisRequest, NewsAnalysisResult
from market_analyst.types.supervisor import SupervisorAnalysisResult
from market_analyst.types.supervisor_chat import (
    SupervisorChatContext,
    SupervisorChatMessage,
    SupervisorChatRequest,
    SupervisorChatResponse,
)
from market_analyst.types.technical import TechnicalAnalysisRequest, TechnicalAnalysisResult


DEFAULT_SUPERVISOR_CHAT_PROMPT = """You are the interactive supervisor chat agent for a stock-analysis workspace.

You answer follow-up questions for one company at a time. Route specialized questions to
the attached worker tools:
- Use ask_fundamental_agent for annual-report, growth, debt, cash-flow, management, and risk questions.
- Use ask_technical_agent for price action, indicators, chart, momentum, support, resistance, and trend questions.
- Use ask_news_agent for recent company news, sector news, sentiment, sources, and watch items.

If the user asks about the existing supervisor rating or overall view, use the supervisor
snapshot in the prompt and call worker tools only when fresh detail is needed. Keep answers
grounded in worker outputs. If a tool cannot provide enough evidence, say what is missing.
"""


def build_supervisor_chat_agent(
    settings: Settings,
    context: SupervisorChatContext,
    *,
    system_prompt: str = DEFAULT_SUPERVISOR_CHAT_PROMPT,
):
    """Build a chat-facing supervisor agent with worker agents attached as tools."""

    model = build_chat_model(settings, temperature=0.1)
    prompt = build_supervisor_chat_prompt(context=context, base_prompt=system_prompt)
    return create_agent(
        model=model,
        tools=build_supervisor_chat_tools(settings=settings, context=context),
        system_prompt=prompt,
    )


def build_supervisor_chat_tools(settings: Settings, context: SupervisorChatContext) -> list[BaseTool]:
    @tool
    def ask_fundamental_agent(question: str) -> str:
        """Ask the RAG-based fundamental worker about annual-report evidence."""

        result = run_fundamental_analysis_agent(
            settings,
            FundamentalAnalysisRequest(
                company_name=context.company_name,
                ticker=context.ticker,
                question=question,
            ),
        )
        return format_fundamental_tool_result(result)

    @tool
    def ask_technical_agent(question: str) -> str:
        """Ask the technical worker about chart, trend, momentum, support, or resistance."""

        result = run_technical_analysis_agent(
            settings,
            TechnicalAnalysisRequest(
                ticker=context.ticker,
                question=question,
            ),
        )
        return format_technical_tool_result(result)

    @tool
    def ask_news_agent(question: str) -> str:
        """Ask the news worker about recent company or sector news and sentiment."""

        result = run_news_analysis_agent(
            settings,
            NewsAnalysisRequest(
                company_name=context.company_name,
                ticker=context.ticker,
                sector=context.sector,
                question=question,
            ),
        )
        return format_news_tool_result(result)

    return [ask_fundamental_agent, ask_technical_agent, ask_news_agent]


def run_supervisor_chat_turn(settings: Settings, request: SupervisorChatRequest) -> SupervisorChatResponse:
    agent = build_supervisor_chat_agent(settings=settings, context=request.context)
    messages = build_supervisor_chat_messages(request)
    result = invoke_agent_with_tracing(
        agent,
        {"messages": messages},
        settings,
        run_name="supervisor-chat-agent",
        tags=("agent", "supervisor", "chat"),
        metadata={
            "company_name": request.context.company_name,
            "ticker": request.context.ticker,
            "sector": request.context.sector,
            "history_messages": len(request.history),
        },
    )
    answer = extract_final_message_content(result)
    return SupervisorChatResponse(
        answer=answer,
        history=append_short_term_history(
            history=request.history,
            user_message=request.message,
            assistant_answer=answer,
            max_history_messages=request.max_history_messages,
        ),
        tool_names=extract_tool_names(result),
    )


def build_supervisor_chat_prompt(*, context: SupervisorChatContext, base_prompt: str = DEFAULT_SUPERVISOR_CHAT_PROMPT) -> str:
    return "\n\n".join(
        [
            base_prompt.strip(),
            "Company context:",
            f"Company: {context.company_name}",
            f"Ticker: {context.ticker}",
            f"Sector: {context.sector or 'Unknown'}",
            "Current supervisor snapshot:",
            summarize_supervisor_snapshot(context.supervisor_result),
        ]
    )


def build_supervisor_chat_messages(request: SupervisorChatRequest) -> list[dict[str, str]]:
    retained_history = trim_short_term_history(request.history, max_messages=request.max_history_messages)
    messages = [{"role": item.role, "content": item.content} for item in retained_history]
    messages.append({"role": "user", "content": request.message})
    return messages


def trim_short_term_history(
    history: Sequence[SupervisorChatMessage],
    *,
    max_messages: int,
) -> list[SupervisorChatMessage]:
    if max_messages <= 0:
        return []
    return list(history[-max_messages:])


def append_short_term_history(
    *,
    history: Sequence[SupervisorChatMessage],
    user_message: str,
    assistant_answer: str,
    max_history_messages: int,
) -> list[SupervisorChatMessage]:
    updated = [
        *history,
        SupervisorChatMessage(role="user", content=user_message),
        SupervisorChatMessage(role="assistant", content=assistant_answer),
    ]
    return trim_short_term_history(updated, max_messages=max_history_messages)


def summarize_supervisor_snapshot(result: SupervisorAnalysisResult | None) -> str:
    if result is None:
        return "No static supervisor run has been attached yet. Use worker tools for evidence."

    components = ", ".join(
        f"{component.name}={component.rating if component.rating is not None else 'missing'}"
        for component in result.components
    )
    return (
        f"Final rating: {result.final_rating}/100. "
        f"Component ratings: {components}. "
        f"Summary: {result.summary}"
    )


def format_fundamental_tool_result(result: FundamentalAnalysisResult) -> str:
    return _format_worker_result(
        worker_name="fundamental",
        rating=result.rating,
        answer=result.answer,
    )


def format_technical_tool_result(result: TechnicalAnalysisResult) -> str:
    return _format_worker_result(
        worker_name="technical",
        rating=result.rating,
        answer=result.answer,
    )


def format_news_tool_result(result: NewsAnalysisResult) -> str:
    return _format_worker_result(
        worker_name="news",
        rating=result.rating,
        answer=result.answer,
    )


def extract_final_message_content(agent_result: dict[str, Any]) -> str:
    messages = agent_result.get("messages", [])
    if not messages:
        return ""
    final_message = messages[-1]
    if hasattr(final_message, "content"):
        content = final_message.content
    elif isinstance(final_message, dict):
        content = final_message.get("content", "")
    else:
        content = str(final_message)
    if isinstance(content, list):
        return "\n".join(str(part) for part in content)
    return str(content)


def extract_tool_names(agent_result: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for message in agent_result.get("messages", []):
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls is None and isinstance(message, dict):
            tool_calls = message.get("tool_calls")
        if not tool_calls:
            continue
        for tool_call in tool_calls:
            if isinstance(tool_call, dict):
                name = tool_call.get("name")
            else:
                name = getattr(tool_call, "name", None)
            if name:
                names.append(str(name))
    return names


def _format_worker_result(*, worker_name: str, rating: int | None, answer: str) -> str:
    rating_text = f"{rating}/100" if rating is not None else "missing"
    return f"{worker_name.title()} worker rating: {rating_text}\n\n{answer}"
