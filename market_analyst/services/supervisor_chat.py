from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from typing import Any

import opik
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, before_agent
from langchain.messages import AIMessage
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

Do not answer questions outside this product scope. Only support market-related questions
about the tracked company, its stock, fundamentals, technicals, news, sector context, and
the current supervisor rating. Refuse unrelated requests such as coding help, general
knowledge, personal advice, math homework, travel, entertainment, or other non-market tasks.
"""

OUT_OF_SCOPE_MESSAGE = (
    "I can only help with market-related questions for this workspace: fundamentals, technicals, "
    "news, sector context, and the current supervisor view for the selected stock. "
    "Please ask a question within that scope."
)

FUTURE_RECOMMENDATION_NOTICE = (
    "Note: Any forward-looking suggestion here is based only on historical and currently available "
    "market information. Future outcomes can change quickly with market conditions."
)

PROMPT_INJECTION_MESSAGE = (
    "I can't help with attempts to override instructions, reveal hidden prompts, or manipulate the "
    "agent behavior. Ask a normal market-analysis question instead."
)

JAILBREAK_MESSAGE = (
    "I can't help with requests to bypass safety controls or change the agent into an unrestricted "
    "mode. Ask a normal market-analysis question instead."
)

MARKET_SCOPE_KEYWORDS = (
    "market",
    "stock",
    "share",
    "price",
    "ticker",
    "company",
    "sector",
    "peer",
    "fundamental",
    "financial",
    "revenue",
    "profit",
    "margin",
    "debt",
    "cash flow",
    "valuation",
    "balance sheet",
    "earnings",
    "guidance",
    "annual report",
    "technical",
    "chart",
    "trend",
    "momentum",
    "support",
    "resistance",
    "breakout",
    "breakdown",
    "rsi",
    "macd",
    "moving average",
    "bollinger",
    "volume",
    "news",
    "headline",
    "sentiment",
    "watch item",
    "supervisor rating",
    "rating",
    "investment",
    "buy",
    "sell",
    "hold",
    "target price",
)

MARKET_FOLLOW_UP_KEYWORDS = (
    "outlook",
    "view",
    "summary",
    "summarize",
    "update",
    "changed",
    "change",
    "compare",
    "comparison",
    "signal",
    "call",
    "conviction",
    "risk",
    "opportunity",
    "position",
    "exposure",
    "entry",
    "exit",
    "accumulate",
    "avoid",
)

OUT_OF_SCOPE_HINT_KEYWORDS = (
    "python",
    "code",
    "coding",
    "function",
    "recipe",
    "travel",
    "trip",
    "flight",
    "hotel",
    "movie",
    "song",
    "poem",
    "joke",
    "email",
    "resume",
    "homework",
    "math",
    "biography",
    "birthday",
)

FUTURE_LOOKING_PATTERNS = (
    r"\bshould i (buy|sell|hold)\b",
    r"\b(can|could) (i|we) (buy|sell|hold)\b",
    r"\brecommend(?:ation)?\b",
    r"\btarget price\b",
    r"\bprice target\b",
    r"\bforecast\b",
    r"\bpredict(?:ion)?\b",
    r"\bprojection\b",
    r"\boutlook\b",
    r"\bgoing forward\b",
    r"\bnext (week|month|quarter|year)\b",
    r"\bwill (?:the )?(stock|share|market|price)\b",
    r"\bexpected\b",
    r"\bupside\b",
    r"\bdownside\b",
)

PROMPT_INJECTION_PATTERNS = (
    r"\bignore (all |any |the )?(previous|prior|above)? ?instructions\b",
    r"\bdisregard (all |any |the )?(previous|prior|above)? ?instructions\b",
    r"\boverride (all |any |the )?instructions\b",
    r"\bforget (all |your |the )?instructions\b",
    r"\breveal (the )?(system|developer|hidden) prompt\b",
    r"\bshow (me )?(the )?(system|developer|hidden) prompt\b",
    r"\bprint (the )?(system|developer) prompt\b",
    r"\bwhat (are|is) (your|the) (system|developer) instructions\b",
    r"\bprompt injection\b",
)

JAILBREAK_PATTERNS = (
    r"\bjailbreak\b",
    r"\bdeveloper mode\b",
    r"\bunfiltered mode\b",
    r"\bbypass (the )?(guardrails|safety|filters|restrictions)\b",
    r"\bdisable (the )?(guardrails|safety|filters|restrictions)\b",
    r"\bdo not follow (the )?(rules|instructions|guardrails)\b",
    r"\bpretend to be (an )?(unfiltered|unrestricted) (assistant|agent)\b",
    r"\bact as (an )?(unfiltered|unrestricted) (assistant|agent)\b",
    r"\bact as dan\b",
)


@before_agent(can_jump_to=["end"], name="supervisor_chat_prompt_injection_guardrail")
def supervisor_chat_prompt_injection_guardrail(state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
    user_message = extract_latest_user_message(state.get("messages", []))
    if not is_prompt_injection_attempt(user_message):
        return None
    return {"messages": [AIMessage(content=PROMPT_INJECTION_MESSAGE)], "jump_to": "end"}


@before_agent(can_jump_to=["end"], name="supervisor_chat_jailbreak_guardrail")
def supervisor_chat_jailbreak_guardrail(state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
    user_message = extract_latest_user_message(state.get("messages", []))
    if not is_jailbreak_attempt(user_message):
        return None
    return {"messages": [AIMessage(content=JAILBREAK_MESSAGE)], "jump_to": "end"}


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
        middleware=build_supervisor_chat_middleware(settings),
    )


def build_supervisor_chat_middleware(settings: Settings) -> list[AgentMiddleware]:
    middleware: list[AgentMiddleware] = [
        supervisor_chat_prompt_injection_guardrail,
        supervisor_chat_jailbreak_guardrail,
    ]
    prompt_shield = build_optional_azure_prompt_shield_middleware(settings)
    if prompt_shield is not None:
        middleware.append(prompt_shield)
    return middleware


def build_optional_azure_prompt_shield_middleware(settings: Settings) -> AgentMiddleware | None:
    if not settings.azure_ai_project_endpoint:
        return None

    try:
        from azure.identity import DefaultAzureCredential
        from langchain_azure_ai.agents.middleware import AzurePromptShieldMiddleware
    except ImportError:
        return None

    return AzurePromptShieldMiddleware(
        project_endpoint=settings.azure_ai_project_endpoint,
        credential=DefaultAzureCredential(),
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


@opik.track(name="supervisor-chat-agent", type="general", tags=["agent", "supervisor", "chat"])
def run_supervisor_chat_turn(settings: Settings, request: SupervisorChatRequest) -> SupervisorChatResponse:
    guardrail_answer = evaluate_supervisor_chat_input_guardrails(request.message, request.context)
    if guardrail_answer is not None:
        return SupervisorChatResponse(
            answer=guardrail_answer,
            history=append_short_term_history(
                history=request.history,
                user_message=request.message,
                assistant_answer=guardrail_answer,
                max_history_messages=request.max_history_messages,
            ),
            tool_names=[],
            guardrail_triggered=True,
        )

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
    answer = maybe_prepend_future_recommendation_notice(
        extract_final_message_content(result),
        request.message,
    )
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


def stream_supervisor_chat_turn(settings: Settings, request: SupervisorChatRequest) -> Iterator[dict[str, object]]:
    guardrail_answer = evaluate_supervisor_chat_input_guardrails(request.message, request.context)
    if guardrail_answer is not None:
        history = append_short_term_history(
            history=request.history,
            user_message=request.message,
            assistant_answer=guardrail_answer,
            max_history_messages=request.max_history_messages,
        )
        yield {
            "type": "final",
            "answer": guardrail_answer,
            "history": [{"role": item.role, "content": item.content} for item in history],
            "toolNames": [],
            "guardrailTriggered": True,
        }
        return

    agent = build_supervisor_chat_agent(settings=settings, context=request.context)
    messages = build_supervisor_chat_messages(request)
    answer_parts: list[str] = []
    fallback_answer = ""
    tool_names: list[str] = []
    prefixed_notice = False

    if is_future_recommendation_request(request.message):
        prefixed_notice = True
        yield {"type": "token", "content": f"{FUTURE_RECOMMENDATION_NOTICE}\n\n"}

    for part in agent.stream({"messages": messages}, stream_mode=["messages", "updates"], version="v2"):
        if not isinstance(part, dict):
            continue

        part_type = part.get("type")
        if part_type == "messages":
            text = extract_stream_message_text(part.get("data"))
            if text:
                answer_parts.append(text)
                yield {"type": "token", "content": text}
            continue

        if part_type == "updates":
            update_data = part.get("data")
            tool_names.extend(extract_tool_names_from_updates(update_data))
            if not fallback_answer:
                fallback_answer = extract_answer_from_updates(update_data)

    answer = "".join(answer_parts).strip() or fallback_answer.strip()
    if prefixed_notice:
        answer = maybe_prepend_future_recommendation_notice(answer, request.message)
    history = append_short_term_history(
        history=request.history,
        user_message=request.message,
        assistant_answer=answer,
        max_history_messages=request.max_history_messages,
    )
    yield {
        "type": "final",
        "answer": answer,
        "history": [{"role": item.role, "content": item.content} for item in history],
        "toolNames": _unique_tool_names(tool_names),
    }


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


def extract_tool_names_from_updates(update_data: object) -> list[str]:
    if not isinstance(update_data, dict):
        return []

    names: list[str] = []
    for value in update_data.values():
        if not isinstance(value, dict):
            continue
        messages = value.get("messages")
        if not isinstance(messages, list):
            continue
        names.extend(extract_tool_names({"messages": messages}))
    return names


def extract_answer_from_updates(update_data: object) -> str:
    if not isinstance(update_data, dict):
        return ""

    for value in update_data.values():
        if not isinstance(value, dict):
            continue
        messages = value.get("messages")
        if not isinstance(messages, list) or not messages:
            continue
        answer = extract_final_message_content({"messages": messages}).strip()
        if answer:
            return answer
    return ""


def extract_stream_message_text(payload: object) -> str:
    if not isinstance(payload, tuple) or len(payload) != 2:
        return ""

    message = payload[0]
    content = getattr(message, "content", "")
    return extract_message_text(content)


def extract_message_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
            continue
        if isinstance(item, dict):
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts)


def _unique_tool_names(names: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def is_out_of_scope_market_question(message: str, context: SupervisorChatContext) -> bool:
    normalized = normalize_text(message)
    if not normalized:
        return True
    if any(keyword in normalized for keyword in OUT_OF_SCOPE_HINT_KEYWORDS):
        return True
    if any(keyword in normalized for keyword in MARKET_SCOPE_KEYWORDS):
        return False
    context_terms = _context_scope_terms(context)
    if any(keyword in normalized for keyword in context_terms) and any(keyword in normalized for keyword in MARKET_FOLLOW_UP_KEYWORDS):
        return False
    return True


def evaluate_supervisor_chat_input_guardrails(message: str, context: SupervisorChatContext | None = None) -> str | None:
    if context is not None and is_out_of_scope_market_question(message, context):
        return OUT_OF_SCOPE_MESSAGE
    if is_prompt_injection_attempt(message):
        return PROMPT_INJECTION_MESSAGE
    if is_jailbreak_attempt(message):
        return JAILBREAK_MESSAGE
    return None


def is_prompt_injection_attempt(message: str) -> bool:
    normalized = normalize_text(message)
    return any(re.search(pattern, normalized) for pattern in PROMPT_INJECTION_PATTERNS)


def is_jailbreak_attempt(message: str) -> bool:
    normalized = normalize_text(message)
    return any(re.search(pattern, normalized) for pattern in JAILBREAK_PATTERNS)


def maybe_prepend_future_recommendation_notice(answer: str, user_message: str) -> str:
    if not answer.strip():
        return answer
    if not is_future_recommendation_request(user_message):
        return answer
    if FUTURE_RECOMMENDATION_NOTICE in answer:
        return answer
    return f"{FUTURE_RECOMMENDATION_NOTICE}\n\n{answer}"


def is_future_recommendation_request(message: str) -> bool:
    normalized = normalize_text(message)
    return any(re.search(pattern, normalized) for pattern in FUTURE_LOOKING_PATTERNS)


def _context_scope_terms(context: SupervisorChatContext) -> tuple[str, ...]:
    company_tokens = tuple(token for token in normalize_text(context.company_name).split() if len(token) >= 3)
    ticker_tokens = tuple(token for token in re.split(r"[^a-z0-9]+", normalize_text(context.ticker)) if token)
    sector_tokens = tuple(token for token in normalize_text(context.sector or "").split() if len(token) >= 3)
    return company_tokens + ticker_tokens + sector_tokens


def normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())


def extract_latest_user_message(messages: object) -> str:
    if not isinstance(messages, list):
        return ""

    for message in reversed(messages):
        role = getattr(message, "type", None) or getattr(message, "role", None)
        if role == "human":
            return extract_message_text(getattr(message, "content", ""))
        if isinstance(message, dict) and message.get("role") == "user":
            return extract_message_text(message.get("content", ""))
    return ""


def _format_worker_result(*, worker_name: str, rating: int | None, answer: str) -> str:
    rating_text = f"{rating}/100" if rating is not None else "missing"
    return f"{worker_name.title()} worker rating: {rating_text}\n\n{answer}"
