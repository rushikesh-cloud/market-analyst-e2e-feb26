from __future__ import annotations

import opik

from market_analyst.config.settings import Settings
from market_analyst.services.agents.fundamental import run_fundamental_analysis_agent
from market_analyst.services.agents.news import run_news_analysis_agent
from market_analyst.services.agents.technical import run_technical_analysis_agent
from market_analyst.services.scoring import normalize_rating
from market_analyst.services.visual_summaries import build_supervisor_visual_summary
from market_analyst.types.fundamental import FundamentalAnalysisRequest, FundamentalAnalysisResult
from market_analyst.types.news import NewsAnalysisRequest, NewsAnalysisResult
from market_analyst.types.supervisor import (
    SupervisorAnalysisRequest,
    SupervisorAnalysisResult,
    SupervisorRatingComponent,
)
from market_analyst.types.technical import TechnicalAnalysisRequest, TechnicalAnalysisResult


DEFAULT_SUPERVISOR_WEIGHTS = {
    "fundamental": 0.45,
    "technical": 0.30,
    "news": 0.25,
}


@opik.track(name="supervisor-agent", type="general", tags=["agent", "supervisor"])
def run_supervisor_agent(
    settings: Settings,
    request: SupervisorAnalysisRequest,
    *,
    weights: dict[str, float] | None = None,
) -> SupervisorAnalysisResult:
    """Run all worker agents and aggregate their 1-100 ratings."""

    fundamental_ticker = request.ticker
    technical_ticker = request.yahoo_finance_ticker or request.ticker

    fundamental = run_fundamental_analysis_agent(
        settings,
        FundamentalAnalysisRequest(
            company_name=request.company_name,
            ticker=fundamental_ticker,
            document_id=request.document_id,
            question=request.fundamental_question,
        ),
    )
    technical = run_technical_analysis_agent(
        settings,
        TechnicalAnalysisRequest(
            ticker=technical_ticker,
            question=request.technical_question,
        ),
    )
    news = run_news_analysis_agent(
        settings,
        NewsAnalysisRequest(
            company_name=request.company_name,
            ticker=technical_ticker,
            sector=request.sector,
            question=request.news_question,
        ),
    )
    return aggregate_supervisor_result(
        company_name=request.company_name,
        ticker=technical_ticker,
        fundamental=fundamental,
        technical=technical,
        news=news,
        weights=weights,
    )


def aggregate_supervisor_result(
    *,
    company_name: str,
    ticker: str,
    fundamental: FundamentalAnalysisResult | None,
    technical: TechnicalAnalysisResult | None,
    news: NewsAnalysisResult | None,
    weights: dict[str, float] | None = None,
) -> SupervisorAnalysisResult:
    normalized_weights = _normalize_weights(weights or DEFAULT_SUPERVISOR_WEIGHTS)
    components = [
        SupervisorRatingComponent(
            name="fundamental",
            rating=fundamental.rating if fundamental else None,
            weight=normalized_weights["fundamental"],
            rationale=_summarize_answer(fundamental.answer if fundamental else ""),
        ),
        SupervisorRatingComponent(
            name="technical",
            rating=technical.rating if technical else None,
            weight=normalized_weights["technical"],
            rationale=_summarize_answer(technical.answer if technical else ""),
        ),
        SupervisorRatingComponent(
            name="news",
            rating=news.rating if news else None,
            weight=normalized_weights["news"],
            rationale=_summarize_answer(news.answer if news else ""),
        ),
    ]
    final_rating = calculate_weighted_rating(components)
    return SupervisorAnalysisResult(
        company_name=company_name,
        ticker=ticker,
        final_rating=final_rating,
        summary=build_supervisor_summary(company_name=company_name, ticker=ticker, final_rating=final_rating, components=components),
        components=components,
        fundamental=fundamental,
        technical=technical,
        news=news,
        metadata={"weights": normalized_weights},
        visual_summary=build_supervisor_visual_summary(
            final_rating=final_rating,
            summary=build_supervisor_summary(company_name=company_name, ticker=ticker, final_rating=final_rating, components=components),
            components=components,
            fundamental=fundamental.visual_summary if fundamental else None,
            technical=technical.visual_summary if technical else None,
            news=news.visual_summary if news else None,
        ),
    )


def calculate_weighted_rating(components: list[SupervisorRatingComponent]) -> int:
    available = [component for component in components if component.rating is not None and component.weight > 0]
    if not available:
        return 50
    weighted_sum = sum(component.rating * component.weight for component in available if component.rating is not None)
    weight_sum = sum(component.weight for component in available)
    return normalize_rating(weighted_sum / weight_sum) or 50


def build_supervisor_summary(
    *,
    company_name: str,
    ticker: str,
    final_rating: int,
    components: list[SupervisorRatingComponent],
) -> str:
    component_text = ", ".join(
        f"{component.name}={component.rating if component.rating is not None else 'missing'}"
        for component in components
    )
    return (
        f"{company_name} ({ticker}) final future-perspective rating is {final_rating}/100. "
        f"Component ratings: {component_text}."
    )


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    values = {name: max(0.0, float(weights.get(name, 0.0))) for name in DEFAULT_SUPERVISOR_WEIGHTS}
    total = sum(values.values())
    if total <= 0:
        return DEFAULT_SUPERVISOR_WEIGHTS.copy()
    return {name: value / total for name, value in values.items()}


def _summarize_answer(answer: str, max_chars: int = 280) -> str:
    summary = " ".join(answer.split())
    if len(summary) > max_chars:
        return f"{summary[:max_chars].rstrip()}..."
    return summary
