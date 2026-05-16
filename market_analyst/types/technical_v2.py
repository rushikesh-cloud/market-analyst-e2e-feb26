from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TechnicalIndicatorConfig:
    name: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TechnicalAnalysisV2Request:
    ticker: str
    question: str | None = None
    period: str = "6mo"
    interval: str = "1d"
    indicators: list[TechnicalIndicatorConfig] = field(default_factory=list)


@dataclass(frozen=True)
class TechnicalChartArtifactV2:
    ticker: str
    chart_path: Path
    period: str
    interval: str
    observation_count: int
    start_date: str
    end_date: str
    latest_close: float
    indicator_names: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TechnicalAnalysisV2Result:
    ticker: str
    question: str
    answer: str
    rating: int | None
    chart_path: Path
    artifact: TechnicalChartArtifactV2
    tool_names: list[str] = field(default_factory=list)
