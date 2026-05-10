from __future__ import annotations

import json
import re
from typing import Any

from langchain.agents import create_agent

from market_analyst.config.settings import Settings
from market_analyst.providers.tavily import build_tavily_search_tool
from market_analyst.services.agent import build_chat_model
from market_analyst.types.news import NewsAnalysisRequest, NewsAnalysisResult


DEFAULT_NEWS_ANALYSIS_QUESTION = (
    "Find recent company-specific and sector-level news. Separate positive and negative "
    "developments, identify material stock implications, and assign a sentiment score "
    "from 0 to 100."
)

DEFAULT_NEWS_AGENT_PROMPT = """You are the news-analysis worker agent for a market intelligence system.

Use Tavily search before answering. Search for both:
1. Recent company and ticker news.
2. Recent sector or peer news that may affect the company.

Focus on news that can plausibly affect investor perception: earnings, guidance, demand,
regulation, litigation, leadership, capital allocation, product launches, credit risk,
macroeconomic pressure, supply chain, analyst actions, and sector rotation.

Return only valid JSON with this schema:
{
  "company_name": "string",
  "ticker": "string",
  "sector": "string or null",
  "sentiment_score": 0,
  "positive_developments": ["string"],
  "negative_developments": ["string"],
  "sector_context": ["string"],
  "stock_implications": ["string"],
  "watch_items": ["string"],
  "sources": [{"title": "string", "url": "string"}]
}

Use a sentiment score above 60 only when recent news is clearly favorable, below 40 only
when recent news is clearly adverse, and 40-60 when mixed or thin. Do not invent sources.
"""


def build_news_analysis_agent(
    settings: Settings,
    *,
    max_results: int = 8,
    time_range: str = "month",
    system_prompt: str = DEFAULT_NEWS_AGENT_PROMPT,
):
    """Build the notebook-facing LangChain news agent backed by Tavily Search."""

    model = build_chat_model(settings, temperature=0.1)
    tavily_search = build_tavily_search_tool(
        settings,
        max_results=max_results,
        topic="news",
        time_range=time_range,
        search_depth="advanced",
        include_answer=False,
        include_raw_content=False,
    )
    return create_agent(model=model, tools=[tavily_search], system_prompt=system_prompt)


def run_news_analysis_agent(settings: Settings, request: NewsAnalysisRequest) -> NewsAnalysisResult:
    agent = build_news_analysis_agent(
        settings,
        max_results=request.max_results,
        time_range=request.time_range,
    )
    question = request.question or DEFAULT_NEWS_ANALYSIS_QUESTION
    prompt = build_news_analysis_prompt(request=request, question=question)
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    answer = extract_final_message_content(result)
    payload = parse_json_object(answer)
    sentiment_score = extract_sentiment_score(payload)
    return NewsAnalysisResult(
        company_name=request.company_name,
        ticker=request.ticker,
        sector=request.sector,
        question=question,
        answer=answer,
        sentiment_score=sentiment_score,
    )


def build_news_analysis_prompt(*, request: NewsAnalysisRequest, question: str) -> str:
    sector_line = request.sector or "Unknown sector; infer likely sector from available news."
    return f"""Company: {request.company_name}
Ticker: {request.ticker}
Sector: {sector_line}
News recency window: {request.time_range}

Task:
{question}

Search instructions:
- Run one company/ticker news search.
- Run one sector-context news search using the company sector or likely peers.
- Prefer recent, source-attributed items.
"""


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


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}

    return parsed if isinstance(parsed, dict) else {}


def extract_sentiment_score(payload: dict[str, Any]) -> int | None:
    value = payload.get("sentiment_score")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return max(0, min(100, value))
    if isinstance(value, float):
        return max(0, min(100, int(round(value))))
    if isinstance(value, str):
        match = re.search(r"\d+(?:\.\d+)?", value)
        if match:
            return max(0, min(100, int(round(float(match.group(0))))))
    return None
