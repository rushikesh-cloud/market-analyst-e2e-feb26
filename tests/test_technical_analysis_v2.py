from pathlib import Path

import pandas as pd

from market_analyst.services.agents.technical_v2 import build_chart_prompt_v2, build_technical_analysis_v2_prompt
from market_analyst.services.charting_v2 import (
    add_technical_indicators_v2,
    generate_technical_chart_v2,
    normalize_indicator_configs,
    parse_indicator_configs_json,
)
from market_analyst.types.technical_v2 import TechnicalAnalysisV2Request, TechnicalIndicatorConfig


def _sample_prices(rows: int = 120) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq="B")
    open_prices = pd.Series([100 + (value * 0.5) for value in range(rows)], index=index, dtype=float)
    close_prices = open_prices + pd.Series([(-1) ** value * 0.8 for value in range(rows)], index=index, dtype=float)
    return pd.DataFrame(
        {
            "Open": open_prices,
            "High": pd.concat([open_prices, close_prices], axis=1).max(axis=1) + 0.9,
            "Low": pd.concat([open_prices, close_prices], axis=1).min(axis=1) - 0.9,
            "Close": close_prices,
            "Volume": [100000 + value * 10 for value in range(rows)],
        },
        index=index,
    )


def test_parse_indicator_configs_json_supports_dynamic_parameters() -> None:
    configs = parse_indicator_configs_json(
        """
        [
          {"name": "rsi", "parameters": {"period": 10, "overbought": 80, "oversold": 25}},
          {"name": "macd", "parameters": {"fast_period": 8, "slow_period": 21, "signal_period": 5}},
          {"name": "bollinger_bands", "parameters": {"window": 15, "num_std": 2.5}}
        ]
        """
    )

    assert [config.name for config in configs] == ["rsi", "macd", "bollinger_bands"]
    assert configs[0].parameters["period"] == 10
    assert configs[1].parameters["slow_period"] == 21
    assert configs[2].parameters["num_std"] == 2.5


def test_generate_technical_chart_v2_writes_png_with_dynamic_panels(tmp_path: Path) -> None:
    indicators = normalize_indicator_configs(
        [
            TechnicalIndicatorConfig(name="bollinger_bands", parameters={"window": 18, "num_std": 2}),
            TechnicalIndicatorConfig(name="rsi", parameters={"period": 12}),
            TechnicalIndicatorConfig(name="macd", parameters={"fast_period": 10, "slow_period": 24, "signal_period": 7}),
        ]
    )
    prices = add_technical_indicators_v2(_sample_prices(), indicators)
    artifact = generate_technical_chart_v2(
        "SAMPLE",
        prices,
        period="1y",
        interval="1d",
        indicators=indicators,
        output_dir=tmp_path,
    )

    assert artifact.chart_path.exists()
    assert artifact.chart_path.suffix == ".png"
    assert artifact.metadata["panels"] == ["price", "rsi", "macd"]
    assert len(artifact.metadata["indicator_snapshots"]) == 3


def test_generate_technical_chart_v2_supports_price_overlay_only(tmp_path: Path) -> None:
    indicators = normalize_indicator_configs(
        [TechnicalIndicatorConfig(name="bollinger_bands", parameters={"window": 20, "num_std": 2})]
    )
    prices = add_technical_indicators_v2(_sample_prices(), indicators)
    artifact = generate_technical_chart_v2(
        "SAMPLE",
        prices,
        period="6mo",
        interval="1h",
        indicators=indicators,
        output_dir=tmp_path,
    )

    assert artifact.chart_path.exists()
    assert artifact.metadata["panels"] == ["price"]
    assert artifact.indicator_names == ["bollinger_bands"]


def test_v2_prompts_preserve_requested_inputs(tmp_path: Path) -> None:
    indicators = [
        TechnicalIndicatorConfig(name="rsi", parameters={"period": 9}),
        TechnicalIndicatorConfig(name="macd", parameters={"fast_period": 6, "slow_period": 19, "signal_period": 4}),
    ]
    request = TechnicalAnalysisV2Request(
        ticker="INFY.NS",
        period="3mo",
        interval="1h",
        indicators=indicators,
        question="Assess momentum and key risks.",
    )

    user_prompt = build_technical_analysis_v2_prompt(request=request, question=request.question or "")

    prices = add_technical_indicators_v2(_sample_prices(), normalize_indicator_configs(indicators))
    artifact = generate_technical_chart_v2(
        "INFY.NS",
        prices,
        period="3mo",
        interval="1h",
        indicators=indicators,
        output_dir=tmp_path,
    )
    chart_prompt = build_chart_prompt_v2(artifact=artifact, question="Assess momentum and key risks.")

    assert "Ticker: INFY.NS" in user_prompt
    assert '"period": 9' in user_prompt
    assert "Interval: 1h" in user_prompt
    assert "chart_path" in chart_prompt
    assert "Indicators:" in chart_prompt
