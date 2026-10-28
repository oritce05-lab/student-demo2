"""Pure technical-indicator math on pandas Series of closing prices."""

from __future__ import annotations

import math

import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window=window, min_periods=window).mean()


def ema(close: pd.Series, span: int) -> pd.Series:
    return close.ewm(span=span, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI. Values range 0-100; above 70 is overbought, below 30 oversold."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss
    out = 100 - 100 / (1 + rs)
    # No losses in the window means maximum strength.
    return out.where(avg_loss != 0, 100.0)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "histogram": macd_line - signal_line})


def bollinger_bands(close: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    middle = sma(close, window)
    std = close.rolling(window=window, min_periods=window).std()
    return pd.DataFrame({"upper": middle + num_std * std, "middle": middle, "lower": middle - num_std * std})


def annualized_volatility(close: pd.Series) -> float:
    returns = close.pct_change().dropna()
    if len(returns) < 2:
        return float("nan")
    return float(returns.std() * math.sqrt(TRADING_DAYS_PER_YEAR))


def max_drawdown(close: pd.Series) -> float:
    """Largest peak-to-trough decline, as a negative fraction (e.g. -0.25 for -25%)."""
    if close.empty:
        return float("nan")
    running_peak = close.cummax()
    return float((close / running_peak - 1).min())


def total_return(close: pd.Series) -> float:
    if len(close) < 2:
        return float("nan")
    return float(close.iloc[-1] / close.iloc[0] - 1)
