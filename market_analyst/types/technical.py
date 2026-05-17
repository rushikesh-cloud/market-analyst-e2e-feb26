from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TechnicalAnalysisRequest:
    ticker: str
    question: str | None = None
    period: str = "6mo"
    interval: str = "1d"


@dataclass(frozen=True)
class TechnicalChartArtifact:
    ticker: str
    chart_path: Path
    observation_count: int
    start_date: str
    end_date: str
    latest_close: float
    latest_ma20: float | None
    latest_ma50: float | None
    latest_rsi: float | None
    latest_macd: float | None
    latest_macd_signal: float | None
    latest_macd_histogram: float | None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TechnicalVisualSummary:
    stance: str | None = None
    trend_state: str | None = None
    momentum_state: str | None = None
    setup: str | None = None
    current_price: float | None = None
    rsi: float | None = None
    distance_to_ma20_pct: float | None = None
    distance_to_ma50_pct: float | None = None
    macd_signal_state: str | None = None
    support_levels: list[str] = field(default_factory=list)
    resistance_levels: list[str] = field(default_factory=list)
    top_risks: list[str] = field(default_factory=list)
    watch_items: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TechnicalAnalysisResult:
    ticker: str
    question: str
    answer: str
    rating: int | None
    chart_path: Path
    artifact: TechnicalChartArtifact
    structured_output: dict[str, Any] = field(default_factory=dict)
    visual_summary: TechnicalVisualSummary | None = None
