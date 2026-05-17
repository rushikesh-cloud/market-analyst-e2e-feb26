from __future__ import annotations

from typing import Any

from market_analyst.config.settings import Settings
from market_analyst.repositories.vector_db import hybrid_search
from market_analyst.services.agent import build_market_analysis_agent
from market_analyst.services.scoring import extract_rating_from_text
from market_analyst.telemetry import invoke_agent_with_tracing
from market_analyst.types.fundamental import FundamentalAnalysisRequest, FundamentalAnalysisResult, FundamentalSourceReference


DEFAULT_FUNDAMENTAL_ANALYSIS_QUESTION = (
    "Use annual-report RAG context to analyze growth, debt, cash flow, profitability, "
    "management commentary, and risks. Assign a fundamental_rating from 1 to 100, "
    "where 100 is most positive for the stock's future perspective."
)

DEFAULT_FUNDAMENTAL_AGENT_PROMPT = """You are the RAG-based fundamental-analysis worker agent.

Use the retrieval tool for factual annual-report context before scoring. Ground the answer
in retrieved chunks and state when the RAG store has insufficient evidence.

Return only valid JSON with this schema:
{
  "company_name": "string",
  "ticker": "string or null",
  "fundamental_rating": 1,
  "growth": ["string"],
  "cash_flow": ["string"],
  "debt_and_balance_sheet": ["string"],
  "risks": ["string"],
  "rationale": "string"
}

The fundamental_rating must be an integer from 1 to 100. Use ratings above 70 only when
fundamental evidence is clearly positive, below 40 when evidence is weak or adverse, and
40-70 for mixed or incomplete evidence.
"""


def build_fundamental_analysis_agent(
    settings: Settings,
    *,
    retrieval_limit: int = 5,
    system_prompt: str = DEFAULT_FUNDAMENTAL_AGENT_PROMPT,
    document_id: str | None = None,
) -> Any:
    """Build the notebook-facing RAG fundamental worker agent."""

    return build_market_analysis_agent(
        settings,
        retrieval_limit=retrieval_limit,
        system_prompt=system_prompt,
        ticker_transform=normalize_fundamental_ticker,
        document_id=document_id,
    )


def run_fundamental_analysis_agent(
    settings: Settings,
    request: FundamentalAnalysisRequest,
) -> FundamentalAnalysisResult:
    question = request.question or DEFAULT_FUNDAMENTAL_ANALYSIS_QUESTION
    normalized_ticker = normalize_fundamental_ticker(request.ticker)
    agent = build_fundamental_analysis_agent(
        settings,
        retrieval_limit=request.retrieval_limit,
        document_id=request.document_id,
    )
    prompt = build_fundamental_analysis_prompt(request=request, question=question)
    result = invoke_agent_with_tracing(
        agent,
        {"messages": [{"role": "user", "content": prompt}]},
        settings,
        run_name="fundamental-analysis-agent",
        tags=("agent", "fundamental"),
        metadata={
            "company_name": request.company_name,
            "ticker": normalized_ticker,
            "document_id": request.document_id,
        },
    )
    answer = extract_final_message_content(result)
    rating = extract_rating_from_text(answer, keys=("fundamental_rating", "rating", "score"))
    sources = compile_fundamental_sources(
        settings,
        query=question,
        ticker=normalized_ticker,
        document_id=request.document_id,
        limit=request.retrieval_limit,
    )
    return FundamentalAnalysisResult(
        company_name=request.company_name,
        ticker=normalized_ticker,
        question=question,
        answer=answer,
        rating=rating,
        sources=sources,
    )


def build_fundamental_analysis_prompt(*, request: FundamentalAnalysisRequest, question: str) -> str:
    normalized_ticker = normalize_fundamental_ticker(request.ticker)
    ticker_line = normalized_ticker or "No ticker provided; search across available report chunks for the company."
    original_ticker_line = f"\nOriginal ticker input: {request.ticker}" if request.ticker and request.ticker != normalized_ticker else ""
    return f"""Company: {request.company_name}
Fundamental RAG ticker: {ticker_line}{original_ticker_line}

Task:
{question}

Instructions:
- Search annual-report RAG context before answering.
- Use the Fundamental RAG ticker for report comparison; exchange suffixes such as `.NS` are for market-data providers and are not used for fundamental report matching.
- Focus on growth, cash flow, debt, profitability, management commentary, and risks.
- Return a fundamental_rating from 1 to 100.
"""


def normalize_fundamental_ticker(ticker: str | None) -> str | None:
    if ticker is None:
        return None
    normalized = ticker.strip().upper().split(".", maxsplit=1)[0].strip()
    return normalized or None


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


def compile_fundamental_sources(
    settings: Settings,
    *,
    query: str,
    ticker: str | None,
    document_id: str | None,
    limit: int,
) -> list[FundamentalSourceReference]:
    rows = hybrid_search(
        settings,
        query=query,
        ticker=ticker,
        document_id=document_id,
        limit=limit,
    )

    sources: list[FundamentalSourceReference] = []
    seen: set[tuple[str | None, int | None, str | None, str | None, str | None]] = set()
    for row in rows:
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        source = FundamentalSourceReference(
            document_name=_read_string(metadata.get("source_file")),
            page_number=_read_page_number(metadata.get("page_number")),
            heading_path=_read_string(metadata.get("heading_path")),
            source_path=_read_string(metadata.get("source_path")),
            chunk_id=_read_string(metadata.get("chunk_id")),
        )
        key = (source.document_name, source.page_number, source.heading_path, source.source_path, source.chunk_id)
        if key in seen:
            continue
        seen.add(key)
        sources.append(source)
    return sources


def _read_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _read_page_number(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    text = _read_string(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None
