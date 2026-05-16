from __future__ import annotations

from dataclasses import dataclass, field

from market_analyst.types.fundamental import FundamentalAnalysisResult
from market_analyst.types.news import NewsAnalysisResult
from market_analyst.types.technical import TechnicalAnalysisResult


@dataclass(frozen=True)
class SupervisorAnalysisRequest:
    company_name: str
    ticker: str
    document_id: str | None = None
    sector: str | None = None
    fundamental_question: str | None = None
    technical_question: str | None = None
    news_question: str | None = None


@dataclass(frozen=True)
class SupervisorRatingComponent:
    name: str
    rating: int | None
    weight: float
    rationale: str


@dataclass(frozen=True)
class SupervisorAnalysisResult:
    company_name: str
    ticker: str
    final_rating: int
    summary: str
    components: list[SupervisorRatingComponent]
    fundamental: FundamentalAnalysisResult | None = None
    technical: TechnicalAnalysisResult | None = None
    news: NewsAnalysisResult | None = None
    metadata: dict[str, object] = field(default_factory=dict)
