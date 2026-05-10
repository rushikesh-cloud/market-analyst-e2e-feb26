from __future__ import annotations

import os

from market_analyst.config.settings import Settings


def build_tavily_search_tool(
    settings: Settings,
    *,
    max_results: int = 8,
    topic: str = "news",
    time_range: str = "month",
    search_depth: str = "advanced",
    include_answer: bool = False,
    include_raw_content: bool = False,
):
    """Build the Tavily LangChain search tool through explicit project settings."""

    settings.require_tavily()
    os.environ.setdefault("TAVILY_API_KEY", settings.tavily_api_key)

    try:
        from langchain_tavily import TavilySearch
    except ImportError as exc:  # pragma: no cover - exercised only when dependency is missing
        raise ImportError(
            "Missing Tavily integration. Install project requirements so "
            "`langchain-tavily` is available."
        ) from exc

    return TavilySearch(
        max_results=max_results,
        topic=topic,
        time_range=time_range,
        search_depth=search_depth,
        include_answer=include_answer,
        include_raw_content=include_raw_content,
    )
