from __future__ import annotations

from typing import Any

from market_analyst.config.settings import Settings
from market_analyst.services.agent import build_market_analysis_agent
from market_analyst.services.scoring import extract_rating_from_text
from market_analyst.types.fundamental import FundamentalAnalysisRequest, FundamentalAnalysisResult


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
) -> Any:
    """Build the notebook-facing RAG fundamental worker agent."""

    return build_market_analysis_agent(
        settings,
        retrieval_limit=retrieval_limit,
        system_prompt=system_prompt,
    )


def run_fundamental_analysis_agent(
    settings: Settings,
    request: FundamentalAnalysisRequest,
) -> FundamentalAnalysisResult:
    question = request.question or DEFAULT_FUNDAMENTAL_ANALYSIS_QUESTION
    agent = build_fundamental_analysis_agent(settings, retrieval_limit=request.retrieval_limit)
    prompt = build_fundamental_analysis_prompt(request=request, question=question)
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    answer = extract_final_message_content(result)
    rating = extract_rating_from_text(answer, keys=("fundamental_rating", "rating", "score"))
    return FundamentalAnalysisResult(
        company_name=request.company_name,
        ticker=request.ticker,
        question=question,
        answer=answer,
        rating=rating,
    )


def build_fundamental_analysis_prompt(*, request: FundamentalAnalysisRequest, question: str) -> str:
    ticker_line = request.ticker or "No ticker provided; search across available report chunks for the company."
    return f"""Company: {request.company_name}
Ticker: {ticker_line}

Task:
{question}

Instructions:
- Search annual-report RAG context before answering.
- Focus on growth, cash flow, debt, profitability, management commentary, and risks.
- Return a fundamental_rating from 1 to 100.
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
