from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from market_analyst.types.technical import TechnicalChartArtifact


def add_technical_indicators(prices: pd.DataFrame) -> pd.DataFrame:
    if prices.empty:
        raise ValueError("prices cannot be empty")

    data = prices.copy()
    close = data["Close"].astype(float)

    data["MA20"] = close.rolling(window=20, min_periods=1).mean()
    data["MA50"] = close.rolling(window=50, min_periods=1).mean()
    data["RSI14"] = _relative_strength_index(close, window=14)

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    data["MACD"] = ema12 - ema26
    data["MACD_SIGNAL"] = data["MACD"].ewm(span=9, adjust=False).mean()
    data["MACD_HIST"] = data["MACD"] - data["MACD_SIGNAL"]
    return data


def generate_technical_chart(
    ticker: str,
    prices_with_indicators: pd.DataFrame,
    output_dir: Path | str = "notebooks/outputs/technical_charts",
) -> TechnicalChartArtifact:
    if prices_with_indicators.empty:
        raise ValueError("prices_with_indicators cannot be empty")

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    symbol = ticker.strip().upper()
    chart_path = output_root / f"{symbol.lower()}_technical_chart.png"

    data = prices_with_indicators.tail(140).copy()
    dates = mdates.date2num(data.index.to_pydatetime())

    fig, axes = plt.subplots(
        nrows=3,
        ncols=1,
        figsize=(13, 9),
        sharex=True,
        gridspec_kw={"height_ratios": [3.2, 1.2, 1.4]},
    )
    fig.suptitle(f"{symbol} Technical Chart", fontsize=15, fontweight="bold")

    price_axis, rsi_axis, macd_axis = axes
    price_axis.plot(data.index, data["Close"], label="Close", color="#0F172A", linewidth=1.8)
    price_axis.plot(data.index, data["MA20"], label="MA20", color="#2563EB", linewidth=1.2)
    price_axis.plot(data.index, data["MA50"], label="MA50", color="#EA580C", linewidth=1.2)
    price_axis.set_ylabel("Price")
    price_axis.grid(True, alpha=0.25)
    price_axis.legend(loc="upper left", ncols=3, fontsize=9)

    rsi_axis.plot(data.index, data["RSI14"], label="RSI14", color="#7C3AED", linewidth=1.4)
    rsi_axis.axhline(70, color="#DC2626", linestyle="--", linewidth=0.9)
    rsi_axis.axhline(30, color="#16A34A", linestyle="--", linewidth=0.9)
    rsi_axis.set_ylim(0, 100)
    rsi_axis.set_ylabel("RSI")
    rsi_axis.grid(True, alpha=0.25)

    histogram_colors = ["#16A34A" if value >= 0 else "#DC2626" for value in data["MACD_HIST"].fillna(0)]
    macd_axis.bar(dates, data["MACD_HIST"], color=histogram_colors, alpha=0.55, width=0.8, label="MACD Hist")
    macd_axis.plot(data.index, data["MACD"], label="MACD", color="#0F766E", linewidth=1.2)
    macd_axis.plot(data.index, data["MACD_SIGNAL"], label="Signal", color="#BE123C", linewidth=1.1)
    macd_axis.axhline(0, color="#475569", linewidth=0.8)
    macd_axis.set_ylabel("MACD")
    macd_axis.grid(True, alpha=0.25)
    macd_axis.legend(loc="upper left", ncols=3, fontsize=9)

    macd_axis.xaxis.set_major_locator(mdates.AutoDateLocator())
    macd_axis.xaxis.set_major_formatter(mdates.ConciseDateFormatter(macd_axis.xaxis.get_major_locator()))
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(chart_path, dpi=160)
    plt.close(fig)

    latest = prices_with_indicators.iloc[-1]
    return TechnicalChartArtifact(
        ticker=symbol,
        chart_path=chart_path,
        observation_count=len(prices_with_indicators),
        start_date=str(prices_with_indicators.index.min().date()),
        end_date=str(prices_with_indicators.index.max().date()),
        latest_close=float(latest["Close"]),
        latest_ma20=_optional_float(latest.get("MA20")),
        latest_ma50=_optional_float(latest.get("MA50")),
        latest_rsi=_optional_float(latest.get("RSI14")),
        latest_macd=_optional_float(latest.get("MACD")),
        latest_macd_signal=_optional_float(latest.get("MACD_SIGNAL")),
        latest_macd_histogram=_optional_float(latest.get("MACD_HIST")),
        metadata={"chart_rows": len(data)},
    )


def summarize_chart_artifact(artifact: TechnicalChartArtifact) -> str:
    return "\n".join(
        [
            f"Ticker: {artifact.ticker}",
            f"Window: {artifact.start_date} to {artifact.end_date}",
            f"Observations: {artifact.observation_count}",
            f"Latest close: {artifact.latest_close:.2f}",
            f"Latest MA20: {_format_optional(artifact.latest_ma20)}",
            f"Latest MA50: {_format_optional(artifact.latest_ma50)}",
            f"Latest RSI14: {_format_optional(artifact.latest_rsi)}",
            f"Latest MACD: {_format_optional(artifact.latest_macd)}",
            f"Latest MACD signal: {_format_optional(artifact.latest_macd_signal)}",
            f"Latest MACD histogram: {_format_optional(artifact.latest_macd_histogram)}",
        ]
    )


def _relative_strength_index(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    relative_strength = avg_gain / avg_loss.mask(avg_loss == 0)
    rsi = 100 - (100 / (1 + relative_strength))
    return rsi.fillna(50)


def _optional_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _format_optional(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"
