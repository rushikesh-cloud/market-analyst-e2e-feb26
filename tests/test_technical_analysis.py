from pathlib import Path

import pandas as pd

from market_analyst.providers.market_data import normalize_price_history
from market_analyst.services.agents.technical import build_multimodal_chart_message, encode_image_data_uri
from market_analyst.services.charting import add_technical_indicators, generate_technical_chart


def _sample_prices(rows: int = 80) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq="B")
    close = pd.Series([100 + index for index in range(rows)], index=index, dtype=float)
    return pd.DataFrame(
        {
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": [100000 + index for index in range(rows)],
        },
        index=index,
    )


def test_normalize_price_history_handles_yfinance_multiindex() -> None:
    base = _sample_prices(5)
    base.columns = pd.MultiIndex.from_product([base.columns, ["SAMPLE"]])

    normalized = normalize_price_history(base, ticker="SAMPLE")

    assert list(normalized.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(normalized) == 5


def test_generate_technical_chart_writes_png(tmp_path: Path) -> None:
    prices = add_technical_indicators(_sample_prices())
    artifact = generate_technical_chart("SAMPLE", prices, output_dir=tmp_path)

    assert artifact.chart_path.exists()
    assert artifact.chart_path.suffix == ".png"
    assert artifact.latest_close > 0
    assert artifact.latest_rsi is not None


def test_multimodal_message_contains_chart_image(tmp_path: Path) -> None:
    prices = add_technical_indicators(_sample_prices())
    artifact = generate_technical_chart("SAMPLE", prices, output_dir=tmp_path)

    data_uri = encode_image_data_uri(artifact.chart_path)
    message = build_multimodal_chart_message(artifact=artifact, question="What is the trend?")

    assert data_uri.startswith("data:image/png;base64,")
    assert message.content[0]["type"] == "text"
    assert message.content[1]["type"] == "image_url"
    assert "What is the trend?" in message.content[0]["text"]
