from __future__ import annotations

import pandas as pd
import yfinance as yf


REQUIRED_PRICE_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def fetch_price_history(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("ticker is required")

    prices = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    prices = normalize_price_history(prices, ticker=symbol)
    if prices.empty:
        raise ValueError(f"No price history returned for ticker {symbol}")
    return prices


def normalize_price_history(prices: pd.DataFrame, ticker: str | None = None) -> pd.DataFrame:
    if prices.empty:
        return prices

    normalized = prices.copy()
    if isinstance(normalized.columns, pd.MultiIndex):
        if ticker and ticker in normalized.columns.get_level_values(-1):
            normalized = normalized.xs(ticker, axis=1, level=-1, drop_level=True)
        else:
            normalized.columns = normalized.columns.get_level_values(0)

    normalized = normalized.rename(columns={column: str(column).title() for column in normalized.columns})
    missing = [column for column in REQUIRED_PRICE_COLUMNS if column not in normalized.columns]
    if missing:
        raise ValueError(f"Price history is missing required columns: {', '.join(missing)}")

    normalized = normalized[REQUIRED_PRICE_COLUMNS].dropna(subset=["Open", "High", "Low", "Close"])
    normalized.index = pd.to_datetime(normalized.index)
    normalized = normalized.sort_index()
    return normalized
