from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from market_analyst.types.fundamental import FundamentalAnalysisResult
from market_analyst.types.news import NewsAnalysisResult
from market_analyst.types.technical import TechnicalAnalysisResult


@dataclass(frozen=True)
class SupervisorAnalysisRequest:
    company_name: str
    ticker: str
    yahoo_finance_ticker: str | None = None
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
class SupervisorVisualComponent:
    name: str
    rating: int | None
    weight_pct: float
    contribution_pct: float | None = None


@dataclass(frozen=True)
class SupervisorVisualSummary:
    stance: str | None = None
    confidence: str | None = None
    decision: str | None = None
    top_positives: list[str] = field(default_factory=list)
    top_risks: list[str] = field(default_factory=list)
    watch_items: list[str] = field(default_factory=list)
    component_contributions: list[SupervisorVisualComponent] = field(default_factory=list)


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
    visual_summary: SupervisorVisualSummary | None = None
    structured_output: dict[str, Any] = field(default_factory=dict)
