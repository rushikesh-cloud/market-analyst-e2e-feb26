from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FundamentalSourceReference:
    document_name: str | None
    page_number: int | None
    heading_path: str | None
    source_path: str | None
    chunk_id: str | None


@dataclass(frozen=True)
class FundamentalAnalysisRequest:
    company_name: str
    ticker: str | None = None
    document_id: str | None = None
    question: str | None = None
    retrieval_limit: int = 5


@dataclass(frozen=True)
class FundamentalVisualSummary:
    stance: str | None = None
    revenue_display: str | None = None
    revenue_growth_pct: float | None = None
    profit_margin_pct: float | None = None
    debt_to_equity: float | None = None
    cash_flow_view: str | None = None
    valuation_view: str | None = None
    top_positives: list[str] = field(default_factory=list)
    top_risks: list[str] = field(default_factory=list)
    watch_items: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FundamentalAnalysisResult:
    company_name: str
    ticker: str | None
    question: str
    answer: str
    rating: int | None
    sources: list[FundamentalSourceReference] = field(default_factory=list)
    structured_output: dict[str, Any] = field(default_factory=dict)
    visual_summary: FundamentalVisualSummary | None = None
