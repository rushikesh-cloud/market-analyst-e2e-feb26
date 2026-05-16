from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


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
    latest_rsi: float | None
    latest_macd: float | None
    latest_macd_signal: float | None
    latest_macd_histogram: float | None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TechnicalAnalysisResult:
    ticker: str
    question: str
    answer: str
    rating: int | None
    chart_path: Path
    artifact: TechnicalChartArtifact
