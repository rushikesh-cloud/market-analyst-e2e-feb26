from __future__ import annotations

from collections.abc import Sequence

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI

from market_analyst.config.settings import Settings
from market_analyst.repositories.vector_db import hybrid_search


DEFAULT_MARKET_AGENT_PROMPT = """You are a market analysis agent for listed-company research.

Use the retrieval tool for factual context before answering questions about annual reports,
growth, debt, cash flow, risk, and management commentary. Keep the final answer grounded in
the returned chunks. If context is missing, state that the current RAG store does not contain
enough evidence instead of guessing.
"""


def build_chat_model(settings: Settings, temperature: float = 0.1) -> AzureChatOpenAI:
    settings.require_chat_model()
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_key,
        api_version=settings.azure_openai_version,
        azure_deployment=settings.azure_openai_chat_deployment,
        temperature=temperature,
    )


def build_market_analysis_agent(
    settings: Settings,
    *,
    retrieval_limit: int = 5,
    system_prompt: str = DEFAULT_MARKET_AGENT_PROMPT,
):
    """Build the notebook-facing LangChain agent object."""

    model = build_chat_model(settings)

    @tool
    def search_fundamental_context(query: str, ticker: str | None = None) -> str:
        """Search stored annual-report chunks with hybrid full-text and vector retrieval."""

        results = hybrid_search(settings, query=query, ticker=ticker, limit=retrieval_limit)
        return format_retrieval_results(results)

    return create_agent(
        model=model,
        tools=[search_fundamental_context],
        system_prompt=system_prompt,
    )


def format_retrieval_results(results: Sequence[dict[str, object]], max_chars: int = 900) -> str:
    if not results:
        return "No matching report chunks were found in the current RAG store."

    lines: list[str] = []
    for index, row in enumerate(results, start=1):
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        heading_path = metadata.get("heading_path") or "Unknown section"
        content = " ".join(str(row.get("content", "")).split())
        snippet = content[:max_chars].rstrip()
        if len(content) > max_chars:
            snippet = f"{snippet}..."
        lines.append(
            "\n".join(
                [
                    f"Result {index}",
                    f"Ticker: {row.get('ticker') or 'UNKNOWN'}",
                    f"Company: {row.get('company_name') or 'UNKNOWN'}",
                    f"Section: {heading_path}",
                    f"RRF Score: {row.get('rrf_score')}",
                    f"Full-text Rank: {row.get('full_text_rank')}",
                    f"Vector Distance: {row.get('vector_distance')}",
                    f"Content: {snippet}",
                ]
            )
        )
    return "\n\n".join(lines)
