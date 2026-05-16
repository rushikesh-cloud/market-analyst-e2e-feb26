from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle

from market_analyst.types.technical_v2 import TechnicalChartArtifactV2, TechnicalIndicatorConfig


SUPPORTED_TECHNICAL_INDICATORS = ("macd", "rsi", "bollinger_bands")
DEFAULT_INDICATOR_CONFIGS = (
    TechnicalIndicatorConfig(name="bollinger_bands", parameters={"window": 20, "num_std": 2.0}),
    TechnicalIndicatorConfig(name="rsi", parameters={"period": 14, "overbought": 70, "oversold": 30}),
    TechnicalIndicatorConfig(name="macd", parameters={"fast_period": 12, "slow_period": 26, "signal_period": 9}),
)


def parse_indicator_configs_json(indicators_json: str | None) -> list[TechnicalIndicatorConfig]:
    if not indicators_json or not indicators_json.strip():
        return normalize_indicator_configs([])

    parsed = json.loads(indicators_json)
    if not isinstance(parsed, list):
        raise ValueError("indicators_json must decode to a list")

    configs: list[TechnicalIndicatorConfig] = []
    for item in parsed:
        if not isinstance(item, dict):
            raise ValueError("Each indicator config must be a JSON object")
        name = str(item.get("name", "")).strip()
        parameters = item.get("parameters", item.get("params", {}))
        if not isinstance(parameters, dict):
            raise ValueError("Indicator parameters must be an object")
        configs.append(TechnicalIndicatorConfig(name=name, parameters=dict(parameters)))
    return normalize_indicator_configs(configs)


def serialize_indicator_configs(configs: Sequence[TechnicalIndicatorConfig]) -> str:
    return json.dumps(
        [{"name": config.name, "parameters": config.parameters} for config in normalize_indicator_configs(configs)],
        indent=2,
        sort_keys=True,
    )


def normalize_indicator_configs(
    configs: Sequence[TechnicalIndicatorConfig] | None,
) -> list[TechnicalIndicatorConfig]:
    if not configs:
        return [replace(config) for config in DEFAULT_INDICATOR_CONFIGS]

    normalized: list[TechnicalIndicatorConfig] = []
    for config in configs:
        name = config.name.strip().lower()
        if name not in SUPPORTED_TECHNICAL_INDICATORS:
            raise ValueError(f"Unsupported technical indicator: {config.name}")
        parameters = _normalize_indicator_parameters(name=name, parameters=config.parameters)
        normalized.append(TechnicalIndicatorConfig(name=name, parameters=parameters))
    return normalized


def add_technical_indicators_v2(
    prices: pd.DataFrame,
    indicators: Sequence[TechnicalIndicatorConfig],
) -> pd.DataFrame:
    if prices.empty:
        raise ValueError("prices cannot be empty")

    data = prices.copy()
    close = data["Close"].astype(float)
    for config in normalize_indicator_configs(indicators):
        if config.name == "rsi":
            period = int(config.parameters["period"])
            data[_rsi_column(period)] = _relative_strength_index(close, window=period)
        elif config.name == "macd":
            fast_period = int(config.parameters["fast_period"])
            slow_period = int(config.parameters["slow_period"])
            signal_period = int(config.parameters["signal_period"])
            ema_fast = close.ewm(span=fast_period, adjust=False).mean()
            ema_slow = close.ewm(span=slow_period, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
            histogram = macd_line - signal_line
            data[_macd_column(fast_period, slow_period, signal_period)] = macd_line
            data[_macd_signal_column(fast_period, slow_period, signal_period)] = signal_line
            data[_macd_histogram_column(fast_period, slow_period, signal_period)] = histogram
        elif config.name == "bollinger_bands":
            window = int(config.parameters["window"])
            num_std = float(config.parameters["num_std"])
            rolling_mean = close.rolling(window=window, min_periods=1).mean()
            rolling_std = close.rolling(window=window, min_periods=1).std().fillna(0.0)
            data[_bb_mid_column(window)] = rolling_mean
            data[_bb_upper_column(window, num_std)] = rolling_mean + (rolling_std * num_std)
            data[_bb_lower_column(window, num_std)] = rolling_mean - (rolling_std * num_std)
    return data


def generate_technical_chart_v2(
    ticker: str,
    prices_with_indicators: pd.DataFrame,
    *,
    period: str,
    interval: str,
    indicators: Sequence[TechnicalIndicatorConfig],
    output_dir: Path | str = "notebooks/outputs/technical_charts_v2",
) -> TechnicalChartArtifactV2:
    if prices_with_indicators.empty:
        raise ValueError("prices_with_indicators cannot be empty")

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    symbol = ticker.strip().upper()
    chart_path = output_root / f"{symbol.lower()}_technical_chart_v2.png"

    normalized_indicators = normalize_indicator_configs(indicators)
    data = _select_chart_window(prices_with_indicators, interval=interval)
    dates = mdates.date2num(data.index.to_pydatetime())
    panels = _build_panels(normalized_indicators)
    ratios = [3.8] + [1.3] * (len(panels) - 1)

    fig, axes = plt.subplots(
        nrows=len(panels),
        ncols=1,
        figsize=(14, 4.2 + (2.3 * len(panels))),
        sharex=True,
        gridspec_kw={"height_ratios": ratios},
    )
    if len(panels) == 1:
        axes = [axes]
    panel_axes = dict(zip(panels, axes, strict=True))
    fig.suptitle(f"{symbol} Technical Chart V2", fontsize=15, fontweight="bold")

    _plot_price_panel(
        panel_axes["price"],
        data=data,
        dates=dates,
        interval=interval,
        indicators=normalized_indicators,
    )
    if "rsi" in panel_axes:
        _plot_rsi_panel(panel_axes["rsi"], data=data, indicators=normalized_indicators)
    if "macd" in panel_axes:
        _plot_macd_panel(panel_axes["macd"], data=data, dates=dates, indicators=normalized_indicators)

    last_axis = axes[-1]
    last_axis.xaxis.set_major_locator(mdates.AutoDateLocator())
    last_axis.xaxis.set_major_formatter(mdates.ConciseDateFormatter(last_axis.xaxis.get_major_locator()))
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(chart_path, dpi=170)
    plt.close(fig)

    latest = prices_with_indicators.iloc[-1]
    snapshots = [_build_indicator_snapshot(latest, config) for config in normalized_indicators]
    return TechnicalChartArtifactV2(
        ticker=symbol,
        chart_path=chart_path,
        period=period,
        interval=interval,
        observation_count=len(prices_with_indicators),
        start_date=str(prices_with_indicators.index.min().date()),
        end_date=str(prices_with_indicators.index.max().date()),
        latest_close=float(latest["Close"]),
        indicator_names=[config.name for config in normalized_indicators],
        metadata={
            "chart_rows": len(data),
            "panels": panels,
            "indicator_configs": [
                {"name": config.name, "parameters": config.parameters} for config in normalized_indicators
            ],
            "indicator_snapshots": snapshots,
        },
    )


def summarize_chart_artifact_v2(artifact: TechnicalChartArtifactV2) -> str:
    lines = [
        f"Ticker: {artifact.ticker}",
        f"Window: {artifact.start_date} to {artifact.end_date}",
        f"Period: {artifact.period}",
        f"Interval: {artifact.interval}",
        f"Observations: {artifact.observation_count}",
        f"Latest close: {artifact.latest_close:.2f}",
        f"Indicators: {', '.join(artifact.indicator_names) or 'none'}",
    ]
    for snapshot in artifact.metadata.get("indicator_snapshots", []):
        if not isinstance(snapshot, dict):
            continue
        values = snapshot.get("values", {})
        if not isinstance(values, dict):
            continue
        metrics = ", ".join(f"{key}={_format_optional(_optional_float(value))}" for key, value in values.items())
        lines.append(f"{snapshot.get('name')}: {metrics}")
    return "\n".join(lines)


def _normalize_indicator_parameters(*, name: str, parameters: dict[str, Any]) -> dict[str, Any]:
    params = dict(parameters)
    if name == "rsi":
        period = int(params.get("period", 14))
        overbought = float(params.get("overbought", 70))
        oversold = float(params.get("oversold", 30))
        if period <= 0:
            raise ValueError("RSI period must be positive")
        return {"period": period, "overbought": overbought, "oversold": oversold}
    if name == "macd":
        fast_period = int(params.get("fast_period", 12))
        slow_period = int(params.get("slow_period", 26))
        signal_period = int(params.get("signal_period", 9))
        if min(fast_period, slow_period, signal_period) <= 0:
            raise ValueError("MACD periods must be positive")
        if fast_period >= slow_period:
            raise ValueError("MACD fast_period must be smaller than slow_period")
        return {
            "fast_period": fast_period,
            "slow_period": slow_period,
            "signal_period": signal_period,
        }
    if name == "bollinger_bands":
        window = int(params.get("window", 20))
        num_std = float(params.get("num_std", 2.0))
        if window <= 0 or num_std <= 0:
            raise ValueError("Bollinger parameters must be positive")
        return {"window": window, "num_std": num_std}
    raise ValueError(f"Unsupported technical indicator: {name}")


def _build_panels(indicators: Sequence[TechnicalIndicatorConfig]) -> list[str]:
    panels = ["price"]
    if any(config.name == "rsi" for config in indicators):
        panels.append("rsi")
    if any(config.name == "macd" for config in indicators):
        panels.append("macd")
    return panels


def _select_chart_window(prices_with_indicators: pd.DataFrame, *, interval: str) -> pd.DataFrame:
    interval_key = interval.strip().lower()
    rows = 180
    if interval_key.endswith("m"):
        rows = 120
    elif interval_key.endswith("h"):
        rows = 140
    elif interval_key.endswith("wk"):
        rows = 104
    return prices_with_indicators.tail(rows).copy()


def _plot_price_panel(
    axis: plt.Axes,
    *,
    data: pd.DataFrame,
    dates: Sequence[float],
    interval: str,
    indicators: Sequence[TechnicalIndicatorConfig],
) -> None:
    width = _candlestick_width(dates, interval=interval)
    for index, (_, row) in enumerate(data.iterrows()):
        x_value = dates[index]
        color = "#16A34A" if float(row["Close"]) >= float(row["Open"]) else "#DC2626"
        axis.vlines(x_value, float(row["Low"]), float(row["High"]), color=color, linewidth=1.0, alpha=0.95)
        lower = min(float(row["Open"]), float(row["Close"]))
        height = max(abs(float(row["Close"]) - float(row["Open"])), 0.001)
        axis.add_patch(
            Rectangle(
                (x_value - (width / 2), lower),
                width,
                height,
                facecolor=color,
                edgecolor=color,
                linewidth=0.8,
                alpha=0.7,
            )
        )

    for config in indicators:
        if config.name != "bollinger_bands":
            continue
        window = int(config.parameters["window"])
        num_std = float(config.parameters["num_std"])
        mid_column = _bb_mid_column(window)
        upper_column = _bb_upper_column(window, num_std)
        lower_column = _bb_lower_column(window, num_std)
        label_suffix = f"BB({window},{num_std:g})"
        axis.plot(data.index, data[mid_column], label=f"{label_suffix} Mid", color="#2563EB", linewidth=1.1)
        axis.plot(data.index, data[upper_column], label=f"{label_suffix} Upper", color="#7C3AED", linewidth=1.0)
        axis.plot(data.index, data[lower_column], label=f"{label_suffix} Lower", color="#7C3AED", linewidth=1.0)

    axis.set_ylabel("Price")
    axis.grid(True, alpha=0.2)
    handles, labels = axis.get_legend_handles_labels()
    if handles:
        axis.legend(loc="upper left", fontsize=8, ncols=2)


def _plot_rsi_panel(axis: plt.Axes, *, data: pd.DataFrame, indicators: Sequence[TechnicalIndicatorConfig]) -> None:
    overbought = 70.0
    oversold = 30.0
    for config in indicators:
        if config.name != "rsi":
            continue
        period = int(config.parameters["period"])
        overbought = float(config.parameters["overbought"])
        oversold = float(config.parameters["oversold"])
        axis.plot(data.index, data[_rsi_column(period)], label=f"RSI({period})", linewidth=1.2)
    axis.axhline(overbought, color="#DC2626", linestyle="--", linewidth=0.9)
    axis.axhline(oversold, color="#16A34A", linestyle="--", linewidth=0.9)
    axis.set_ylim(0, 100)
    axis.set_ylabel("RSI")
    axis.grid(True, alpha=0.2)
    axis.legend(loc="upper left", fontsize=8)


def _plot_macd_panel(
    axis: plt.Axes,
    *,
    data: pd.DataFrame,
    dates: Sequence[float],
    indicators: Sequence[TechnicalIndicatorConfig],
) -> None:
    for config in indicators:
        if config.name != "macd":
            continue
        fast_period = int(config.parameters["fast_period"])
        slow_period = int(config.parameters["slow_period"])
        signal_period = int(config.parameters["signal_period"])
        macd_column = _macd_column(fast_period, slow_period, signal_period)
        signal_column = _macd_signal_column(fast_period, slow_period, signal_period)
        histogram_column = _macd_histogram_column(fast_period, slow_period, signal_period)
        histogram_colors = [
            "#16A34A" if value >= 0 else "#DC2626" for value in data[histogram_column].fillna(0)
        ]
        axis.bar(
            dates,
            data[histogram_column],
            color=histogram_colors,
            alpha=0.45,
            width=max(_candlestick_width(dates, interval="1d"), 0.35),
            label=f"MACD Hist ({fast_period},{slow_period},{signal_period})",
        )
        axis.plot(data.index, data[macd_column], label=f"MACD({fast_period},{slow_period})", linewidth=1.1)
        axis.plot(data.index, data[signal_column], label=f"Signal({signal_period})", linewidth=1.0)
    axis.axhline(0, color="#475569", linewidth=0.8)
    axis.set_ylabel("MACD")
    axis.grid(True, alpha=0.2)
    axis.legend(loc="upper left", fontsize=8)


def _build_indicator_snapshot(latest: pd.Series, config: TechnicalIndicatorConfig) -> dict[str, Any]:
    if config.name == "rsi":
        period = int(config.parameters["period"])
        return {
            "name": f"rsi({period})",
            "parameters": dict(config.parameters),
            "values": {"rsi": _optional_float(latest.get(_rsi_column(period)))},
        }
    if config.name == "macd":
        fast_period = int(config.parameters["fast_period"])
        slow_period = int(config.parameters["slow_period"])
        signal_period = int(config.parameters["signal_period"])
        return {
            "name": f"macd({fast_period},{slow_period},{signal_period})",
            "parameters": dict(config.parameters),
            "values": {
                "macd": _optional_float(latest.get(_macd_column(fast_period, slow_period, signal_period))),
                "signal": _optional_float(latest.get(_macd_signal_column(fast_period, slow_period, signal_period))),
                "histogram": _optional_float(
                    latest.get(_macd_histogram_column(fast_period, slow_period, signal_period))
                ),
            },
        }
    window = int(config.parameters["window"])
    num_std = float(config.parameters["num_std"])
    return {
        "name": f"bollinger_bands({window},{num_std:g})",
        "parameters": dict(config.parameters),
        "values": {
            "mid": _optional_float(latest.get(_bb_mid_column(window))),
            "upper": _optional_float(latest.get(_bb_upper_column(window, num_std))),
            "lower": _optional_float(latest.get(_bb_lower_column(window, num_std))),
        },
    }


def _relative_strength_index(close: pd.Series, *, window: int) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    relative_strength = avg_gain / avg_loss.mask(avg_loss == 0)
    rsi = 100 - (100 / (1 + relative_strength))
    return rsi.fillna(50)


def _candlestick_width(dates: Sequence[float], *, interval: str) -> float:
    if len(dates) < 2:
        return 0.6
    spacing = min(max(float(dates[1] - dates[0]), 0.02), 5.0)
    interval_key = interval.strip().lower()
    if interval_key.endswith("m") or interval_key.endswith("h"):
        return spacing * 0.75
    return spacing * 0.65


def _rsi_column(period: int) -> str:
    return f"RSI_{period}"


def _macd_column(fast_period: int, slow_period: int, signal_period: int) -> str:
    return f"MACD_{fast_period}_{slow_period}_{signal_period}"


def _macd_signal_column(fast_period: int, slow_period: int, signal_period: int) -> str:
    return f"MACD_SIGNAL_{fast_period}_{slow_period}_{signal_period}"


def _macd_histogram_column(fast_period: int, slow_period: int, signal_period: int) -> str:
    return f"MACD_HIST_{fast_period}_{slow_period}_{signal_period}"


def _bb_mid_column(window: int) -> str:
    return f"BB_MID_{window}"


def _bb_upper_column(window: int, num_std: float) -> str:
    return f"BB_UPPER_{window}_{_float_token(num_std)}"


def _bb_lower_column(window: int, num_std: float) -> str:
    return f"BB_LOWER_{window}_{_float_token(num_std)}"


def _float_token(value: float) -> str:
    return str(value).replace(".", "_")


def _optional_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _format_optional(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"
