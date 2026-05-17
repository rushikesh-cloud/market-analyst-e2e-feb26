from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import opik
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from market_analyst.config.settings import Settings
from market_analyst.providers.market_data import fetch_price_history
from market_analyst.services.agent import build_chat_model
from market_analyst.services.charting_v2 import (
    add_technical_indicators_v2,
    generate_technical_chart_v2 as generate_chart_artifact_v2,
    normalize_indicator_configs,
    parse_indicator_configs_json,
    serialize_indicator_configs,
    summarize_chart_artifact_v2,
)
from market_analyst.services.scoring import extract_rating_from_text
from market_analyst.telemetry import invoke_agent_with_tracing, invoke_model_with_tracing
from market_analyst.types.technical_v2 import (
    TechnicalAnalysisV2Request,
    TechnicalAnalysisV2Result,
    TechnicalChartArtifactV2,
)


DEFAULT_TECHNICAL_V2_QUESTION = (
    "Analyze the generated technical chart. Explain trend, momentum, support/resistance, "
    "indicator alignment, and a technical score from 1 to 100."
)

DEFAULT_TECHNICAL_V2_PROMPT = """You are the technical-analysis V2 worker agent for a market intelligence system.

You must use tools before answering:
1. Call `generate_technical_chart_v2` with the exact ticker, period, interval, and indicator JSON provided by the user.
2. Then call `analyze_technical_chart_v2` using the returned chart_id and the user's question.

Never answer from memory without generating the chart first.
Keep the final response grounded in the generated chart and requested indicators only.

Return only valid JSON with this schema:
{
  "ticker": "string",
  "period": "string",
  "interval": "string",
  "indicators": [{"name": "string", "parameters": {}}],
  "chart_path": "string",
  "technical_rating": 1,
  "trend": "string",
  "momentum": "string",
  "support_resistance": "string",
  "indicator_insights": ["string"],
  "risks": ["string"],
  "summary": "string"
}

The technical_rating must be an integer from 1 to 100, where 100 is most positive.
Do not mention indicators that were not requested.
"""


def build_technical_analysis_v2_agent(
    settings: Settings,
    *,
    output_dir: Path | str = "notebooks/outputs/technical_charts_v2",
    system_prompt: str = DEFAULT_TECHNICAL_V2_PROMPT,
):
    model = build_chat_model(settings, temperature=0.1)
    runtime_state: dict[str, Any] = {"artifacts": {}, "latest_chart_id": None, "counter": 0}
    output_root = Path(output_dir)

    @tool
    def generate_technical_chart_v2(
        ticker: str,
        period: str = "6mo",
        interval: str = "1d",
        indicators_json: str = "[]",
    ) -> str:
        """Fetch market data and generate a technical chart for the requested ticker and indicators."""

        indicators = parse_indicator_configs_json(indicators_json)
        prices = fetch_price_history(ticker, period=period, interval=interval)
        enriched_prices = add_technical_indicators_v2(prices, indicators)
        artifact = generate_chart_artifact_v2(
            ticker,
            enriched_prices,
            period=period,
            interval=interval,
            indicators=indicators,
            output_dir=output_root,
        )
        runtime_state["counter"] += 1
        chart_id = f"technical-v2-chart-{runtime_state['counter']}"
        runtime_state["artifacts"][chart_id] = artifact
        runtime_state["latest_chart_id"] = chart_id
        return json.dumps(
            {
                "chart_id": chart_id,
                "ticker": artifact.ticker,
                "period": period,
                "interval": interval,
                "chart_path": str(artifact.chart_path),
                "indicator_configs": [{"name": item.name, "parameters": item.parameters} for item in indicators],
                "chart_summary": summarize_chart_artifact_v2(artifact),
            }
        )

    @tool
    def analyze_technical_chart_v2(
        chart_id: str,
        question: str = DEFAULT_TECHNICAL_V2_QUESTION,
    ) -> str:
        """Run multimodal chart analysis on a previously generated chart and return structured JSON."""

        artifact = runtime_state["artifacts"].get(chart_id)
        if artifact is None:
            raise ValueError(f"Unknown chart_id: {chart_id}")
        return analyze_technical_chart_v2_artifact(settings, artifact=artifact, question=question)

    agent = create_agent(
        model=model,
        tools=[generate_technical_chart_v2, analyze_technical_chart_v2],
        system_prompt=system_prompt,
    )
    return agent, runtime_state


@opik.track(name="technical-analysis-agent-v2", type="general", tags=["agent", "technical", "technical-v2"])
def run_technical_analysis_agent_v2(
    settings: Settings,
    request: TechnicalAnalysisV2Request,
    *,
    output_dir: Path | str = "notebooks/outputs/technical_charts_v2",
) -> TechnicalAnalysisV2Result:
    question = request.question or DEFAULT_TECHNICAL_V2_QUESTION
    agent, runtime_state = build_technical_analysis_v2_agent(settings=settings, output_dir=output_dir)
    prompt = build_technical_analysis_v2_prompt(request=request, question=question)
    result = invoke_agent_with_tracing(
        agent,
        {"messages": [{"role": "user", "content": prompt}]},
        settings,
        run_name="technical-analysis-agent-v2",
        tags=("agent", "technical", "technical-v2"),
        metadata={
            "ticker": request.ticker,
            "period": request.period,
            "interval": request.interval,
        },
    )
    answer = extract_final_message_content(result)
    rating = extract_rating_from_text(answer, keys=("technical_rating", "technical_score", "rating", "score"))
    chart_id = runtime_state.get("latest_chart_id")
    artifact = runtime_state.get("artifacts", {}).get(chart_id)
    if artifact is None:
        raise RuntimeError("Technical V2 agent did not generate a chart artifact")
    return TechnicalAnalysisV2Result(
        ticker=artifact.ticker,
        question=question,
        answer=answer,
        rating=rating,
        chart_path=artifact.chart_path,
        artifact=artifact,
        tool_names=extract_tool_names(result),
    )


def build_technical_analysis_v2_prompt(*, request: TechnicalAnalysisV2Request, question: str) -> str:
    indicators = normalize_indicator_configs(request.indicators)
    return "\n".join(
        [
            f"Ticker: {request.ticker}",
            f"Period: {request.period}",
            f"Interval: {request.interval}",
            "Indicator JSON:",
            serialize_indicator_configs(indicators),
            "Task:",
            question,
            "Use the exact ticker, period, interval, and indicator JSON above.",
        ]
    )


@opik.track(name="technical-chart-analysis-v2", type="llm", tags=["sub-agent", "technical", "technical-v2", "multimodal"])
def analyze_technical_chart_v2_artifact(
    settings: Settings,
    *,
    artifact: TechnicalChartArtifactV2,
    question: str,
) -> str:
    model = build_chat_model(settings, temperature=0.1)
    response = invoke_model_with_tracing(
        model,
        [build_multimodal_chart_message_v2(artifact=artifact, question=question)],
        settings,
        run_name="technical-chart-analysis-v2",
        tags=("llm", "technical", "technical-v2", "multimodal"),
        metadata={
            "ticker": artifact.ticker,
            "period": artifact.period,
            "interval": artifact.interval,
            "chart_path": str(artifact.chart_path),
        },
    )
    return str(response.content)


def build_multimodal_chart_message_v2(
    *,
    artifact: TechnicalChartArtifactV2,
    question: str,
) -> HumanMessage:
    prompt = build_chart_prompt_v2(artifact=artifact, question=question)
    return HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": encode_image_data_uri(artifact.chart_path)}},
        ]
    )


def build_chart_prompt_v2(*, artifact: TechnicalChartArtifactV2, question: str) -> str:
    return f"""You are the multimodal technical-analysis stage for a market intelligence system.

Use the attached chart image as the primary evidence. Focus only on the requested indicator
configuration shown in the metadata below.

Return only valid JSON with this schema:
{{
  "ticker": "string",
  "period": "string",
  "interval": "string",
  "chart_path": "string",
  "technical_rating": 1,
  "trend": "string",
  "momentum": "string",
  "support_resistance": "string",
  "indicator_insights": ["string"],
  "risks": ["string"],
  "summary": "string"
}}

The technical_rating must be an integer from 1 to 100.

Chart metadata:
{summarize_chart_artifact_v2(artifact)}

Chart path:
{artifact.chart_path}

Question:
{question}
"""


def encode_image_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


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


def extract_tool_names(agent_result: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for message in agent_result.get("messages", []):
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls is None and isinstance(message, dict):
            tool_calls = message.get("tool_calls")
        if not tool_calls:
            continue
        for tool_call in tool_calls:
            if isinstance(tool_call, dict):
                name = tool_call.get("name")
            else:
                name = getattr(tool_call, "name", None)
            if name:
                names.append(str(name))
    return names
