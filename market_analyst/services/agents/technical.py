from __future__ import annotations

import base64
from pathlib import Path

from langchain_core.messages import HumanMessage

from market_analyst.config.settings import Settings
from market_analyst.providers.market_data import fetch_price_history
from market_analyst.services.agent import build_chat_model
from market_analyst.services.charting import (
    add_technical_indicators,
    generate_technical_chart,
    summarize_chart_artifact,
)
from market_analyst.services.scoring import extract_rating_from_text
from market_analyst.telemetry import invoke_model_with_tracing
from market_analyst.types.technical import (
    TechnicalAnalysisRequest,
    TechnicalAnalysisResult,
    TechnicalChartArtifact,
)


DEFAULT_TECHNICAL_QUESTION = (
    "Analyze the chart and explain the trend, momentum, support/resistance areas, "
    "breakout or breakdown risk, and a technical score from 0 to 100."
)


def run_technical_analysis_agent(
    settings: Settings,
    request: TechnicalAnalysisRequest,
    *,
    output_dir: Path | str = "notebooks/outputs/technical_charts",
) -> TechnicalAnalysisResult:
    question = request.question or DEFAULT_TECHNICAL_QUESTION
    prices = fetch_price_history(request.ticker, period=request.period, interval=request.interval)
    prices_with_indicators = add_technical_indicators(prices)
    artifact = generate_technical_chart(request.ticker, prices_with_indicators, output_dir=output_dir)
    answer = analyze_technical_chart(settings, artifact=artifact, question=question)
    rating = extract_rating_from_text(answer, keys=("technical_rating", "technical_score", "rating", "score"))
    return TechnicalAnalysisResult(
        ticker=artifact.ticker,
        question=question,
        answer=answer,
        rating=rating,
        chart_path=artifact.chart_path,
        artifact=artifact,
    )


def analyze_technical_chart(
    settings: Settings,
    *,
    artifact: TechnicalChartArtifact,
    question: str,
) -> str:
    model = build_chat_model(settings, temperature=0.1)
    message = build_multimodal_chart_message(artifact=artifact, question=question)
    response = invoke_model_with_tracing(
        model,
        [message],
        settings,
        run_name="technical-chart-analysis",
        tags=("llm", "technical", "multimodal"),
        metadata={
            "ticker": artifact.ticker,
            "chart_path": str(artifact.chart_path),
        },
    )
    return str(response.content)


def build_multimodal_chart_message(
    *,
    artifact: TechnicalChartArtifact,
    question: str,
) -> HumanMessage:
    prompt = build_chart_prompt(artifact=artifact, question=question)
    return HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": encode_image_data_uri(artifact.chart_path)}},
        ]
    )


def build_chart_prompt(*, artifact: TechnicalChartArtifact, question: str) -> str:
    return f"""You are the technical-analysis worker agent for a market intelligence system.

Use the attached chart image as the primary evidence. The chart includes close price,
20-day and 50-day moving averages, RSI14, and MACD. Answer the user's question with
specific observations from the chart.

Return only valid JSON with this schema:
{{
  "ticker": "string",
  "technical_rating": 1,
  "trend": "string",
  "momentum": "string",
  "support_resistance": "string",
  "risks": ["string"],
  "rationale": "string"
}}

The technical_rating must be an integer from 1 to 100, where 100 is most positive
for the stock's future perspective.

Chart metadata:
{summarize_chart_artifact(artifact)}

Question:
{question}
"""


def encode_image_data_uri(path: Path) -> str:
    image_bytes = path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"
