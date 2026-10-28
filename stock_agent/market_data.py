"""Market-data tools the agent can call. Each returns a JSON-serializable dict.

Data comes from Yahoo Finance via yfinance. Tel Aviv Stock Exchange tickers use
the ".TA" suffix (e.g. "TEVA.TA", "LUMI.TA").
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd
import yfinance as yf

from . import indicators

VALID_PERIODS = ["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
VALID_INTERVALS = ["1d", "1wk", "1mo"]
MAX_HISTORY_ROWS = 60


class ToolError(Exception):
    """A problem the model should see and can recover from (bad ticker, bad period...)."""


def _clean(value: Any) -> Any:
    """Make numpy/pandas values JSON-friendly and round floats."""
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp,)):
        return value.strftime("%Y-%m-%d")
    if hasattr(value, "item"):  # numpy scalar
        value = value.item()
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else round(value, 4)
    return value


def _history(symbol: str, period: str = "1y", interval: str = "1d", auto_adjust: bool = True) -> pd.DataFrame:
    """Price bars. auto_adjust=True folds dividends into past prices (right for returns);
    False keeps the traded prices (right for "price moved X% today")."""
    if period not in VALID_PERIODS:
        raise ToolError(f"Invalid period '{period}'. Use one of: {', '.join(VALID_PERIODS)}")
    if interval not in VALID_INTERVALS:
        raise ToolError(f"Invalid interval '{interval}'. Use one of: {', '.join(VALID_INTERVALS)}")
    df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=auto_adjust)
    if df.empty:
        raise ToolError(f"No price data found for '{symbol}'. Check the ticker (TASE stocks end with .TA).")
    return df


def get_quote(symbol: str) -> dict:
    symbol = symbol.upper().strip()
    ticker = yf.Ticker(symbol)
    info = ticker.info or {}
    df = _history(symbol, period="5d")
    last = df["Close"].iloc[-1]
    prev = df["Close"].iloc[-2] if len(df) > 1 else last
    return {
        "symbol": symbol,
        "name": info.get("longName") or info.get("shortName"),
        "currency": info.get("currency"),
        "exchange": info.get("exchange"),
        "last_close_date": _clean(df.index[-1]),
        "price": _clean(last),
        "change": _clean(last - prev),
        "change_pct": _clean((last / prev - 1) * 100),
        "day_high": _clean(df["High"].iloc[-1]),
        "day_low": _clean(df["Low"].iloc[-1]),
        "volume": _clean(df["Volume"].iloc[-1]),
        "fifty_two_week_high": _clean(info.get("fiftyTwoWeekHigh")),
        "fifty_two_week_low": _clean(info.get("fiftyTwoWeekLow")),
        "market_cap": _clean(info.get("marketCap")),
        "trailing_pe": _clean(info.get("trailingPE")),
        "forward_pe": _clean(info.get("forwardPE")),
        "dividend_yield": _clean(info.get("dividendYield")),
    }


def get_price_history(symbol: str, period: str = "6mo", interval: str = "1d") -> dict:
    symbol = symbol.upper().strip()
    df = _history(symbol, period, interval)
    close = df["Close"]
    # Keep the payload small: sample evenly down to MAX_HISTORY_ROWS, always keeping the latest row.
    step = max(1, math.ceil(len(df) / MAX_HISTORY_ROWS))
    sampled = df.iloc[::-1][::step].iloc[::-1]
    return {
        "symbol": symbol,
        "period": period,
        "interval": interval,
        "start": _clean(df.index[0]),
        "end": _clean(df.index[-1]),
        "first_close": _clean(close.iloc[0]),
        "last_close": _clean(close.iloc[-1]),
        "high": _clean(df["High"].max()),
        "low": _clean(df["Low"].min()),
        "total_return_pct": _clean(indicators.total_return(close) * 100),
        "annualized_volatility_pct": _clean(indicators.annualized_volatility(close) * 100),
        "max_drawdown_pct": _clean(indicators.max_drawdown(close) * 100),
        "rows_sampled_every": step,
        "closes": [{"date": _clean(i), "close": _clean(c)} for i, c in sampled["Close"].items()],
    }


def get_technical_indicators(symbol: str) -> dict:
    symbol = symbol.upper().strip()
    # Two years of daily data gives the 200-day average room to warm up.
    close = _history(symbol, period="2y")["Close"]
    price = close.iloc[-1]
    sma20, sma50, sma200 = (indicators.sma(close, w).iloc[-1] for w in (20, 50, 200))
    rsi14 = indicators.rsi(close).iloc[-1]
    macd = indicators.macd(close).iloc[-1]
    bands = indicators.bollinger_bands(close).iloc[-1]

    signals = []
    if not math.isnan(sma50) and not math.isnan(sma200):
        signals.append("golden-cross regime (SMA50 > SMA200)" if sma50 > sma200 else "death-cross regime (SMA50 < SMA200)")
    if not math.isnan(sma200):
        signals.append("price above SMA200" if price > sma200 else "price below SMA200")
    if rsi14 >= 70:
        signals.append("RSI overbought (>=70)")
    elif rsi14 <= 30:
        signals.append("RSI oversold (<=30)")
    signals.append("MACD above signal (bullish momentum)" if macd["macd"] > macd["signal"] else "MACD below signal (bearish momentum)")
    if price > bands["upper"]:
        signals.append("price above upper Bollinger band")
    elif price < bands["lower"]:
        signals.append("price below lower Bollinger band")

    return {
        "symbol": symbol,
        "as_of": _clean(close.index[-1]),
        "price": _clean(price),
        "sma_20": _clean(sma20),
        "sma_50": _clean(sma50),
        "sma_200": _clean(sma200),
        "rsi_14": _clean(rsi14),
        "macd": _clean(macd["macd"]),
        "macd_signal": _clean(macd["signal"]),
        "macd_histogram": _clean(macd["histogram"]),
        "bollinger_upper": _clean(bands["upper"]),
        "bollinger_lower": _clean(bands["lower"]),
        "return_1m_pct": _clean((price / close.iloc[-22] - 1) * 100) if len(close) > 22 else None,
        "return_6m_pct": _clean((price / close.iloc[-127] - 1) * 100) if len(close) > 127 else None,
        "return_1y_pct": _clean((price / close.iloc[-253] - 1) * 100) if len(close) > 253 else None,
        "signals": signals,
    }


def get_company_info(symbol: str) -> dict:
    symbol = symbol.upper().strip()
    info = yf.Ticker(symbol).info or {}
    if not info.get("longName") and not info.get("shortName"):
        raise ToolError(f"No company information found for '{symbol}'.")
    keys = [
        "longName", "sector", "industry", "country", "website", "fullTimeEmployees",
        "marketCap", "enterpriseValue", "trailingPE", "forwardPE", "priceToBook", "pegRatio",
        "profitMargins", "operatingMargins", "returnOnEquity", "revenueGrowth", "earningsGrowth",
        "totalRevenue", "totalDebt", "totalCash", "debtToEquity", "freeCashflow",
        "dividendYield", "payoutRatio", "beta", "recommendationKey", "targetMeanPrice",
        "numberOfAnalystOpinions",
    ]
    result = {"symbol": symbol, **{k: _clean(info.get(k)) for k in keys}}
    summary = info.get("longBusinessSummary") or ""
    result["business_summary"] = summary[:1500]
    return result


def compare_stocks(symbols: list[str], period: str = "1y") -> dict:
    symbols = [s.upper().strip() for s in symbols]
    if not 2 <= len(symbols) <= 8:
        raise ToolError("Provide between 2 and 8 symbols to compare.")
    closes = {s: _history(s, period)["Close"] for s in symbols}
    rows = [
        {
            "symbol": s,
            "last_close": _clean(c.iloc[-1]),
            "total_return_pct": _clean(indicators.total_return(c) * 100),
            "annualized_volatility_pct": _clean(indicators.annualized_volatility(c) * 100),
            "max_drawdown_pct": _clean(indicators.max_drawdown(c) * 100),
        }
        for s, c in closes.items()
    ]
    # Align on dates before correlating; exchanges have different holidays and time zones.
    aligned = pd.DataFrame({s: c.tz_localize(None) if c.index.tz else c for s, c in closes.items()})
    aligned.index = aligned.index.normalize()
    corr = aligned.pct_change().dropna(how="any").corr()
    return {
        "period": period,
        "stocks": sorted(rows, key=lambda r: r["total_return_pct"] or -1e9, reverse=True),
        "daily_return_correlation": {a: {b: _clean(corr.loc[a, b]) for b in symbols} for a in symbols},
    }


def get_news(symbol: str, limit: int = 8) -> dict:
    symbol = symbol.upper().strip()
    items = yf.Ticker(symbol).news or []
    news = []
    for item in items[: max(1, min(limit, 20))]:
        content = item.get("content", item)  # newer yfinance nests fields under "content"
        provider = content.get("provider")
        url = content.get("canonicalUrl") or content.get("clickThroughUrl")
        news.append({
            "title": content.get("title"),
            "publisher": provider.get("displayName") if isinstance(provider, dict) else content.get("publisher"),
            "published": content.get("pubDate") or content.get("providerPublishTime"),
            "summary": (content.get("summary") or "")[:400],
            "url": url.get("url") if isinstance(url, dict) else content.get("link"),
        })
    return {"symbol": symbol, "news": news}


TOOLS: dict[str, Any] = {
    "get_quote": get_quote,
    "get_price_history": get_price_history,
    "get_technical_indicators": get_technical_indicators,
    "get_company_info": get_company_info,
    "compare_stocks": compare_stocks,
    "get_news": get_news,
}

_SYMBOL = {"type": "string", "description": "Ticker symbol, e.g. AAPL, NVDA, ^GSPC, or TEVA.TA for Tel Aviv."}

TOOL_DEFINITIONS = [
    {
        "name": "get_quote",
        "description": "Latest price, daily change, volume, 52-week range, market cap and P/E for one stock or index.",
        "input_schema": {"type": "object", "properties": {"symbol": _SYMBOL}, "required": ["symbol"]},
    },
    {
        "name": "get_price_history",
        "description": "Price history summary for a period: return, volatility, max drawdown, high/low, and a sampled series of closes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": _SYMBOL,
                "period": {"type": "string", "enum": VALID_PERIODS, "description": "Lookback window. Default 6mo."},
                "interval": {"type": "string", "enum": VALID_INTERVALS, "description": "Bar size. Default 1d."},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_technical_indicators",
        "description": "Technical analysis on daily data: SMA 20/50/200, RSI(14), MACD, Bollinger bands, 1m/6m/1y returns, and plain-language signals.",
        "input_schema": {"type": "object", "properties": {"symbol": _SYMBOL}, "required": ["symbol"]},
    },
    {
        "name": "get_company_info",
        "description": "Company profile and fundamentals: sector, business summary, margins, growth, debt, valuation ratios, analyst consensus.",
        "input_schema": {"type": "object", "properties": {"symbol": _SYMBOL}, "required": ["symbol"]},
    },
    {
        "name": "compare_stocks",
        "description": "Compare 2-8 stocks over a period: return, volatility, max drawdown, and correlation of daily returns.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbols": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 8},
                "period": {"type": "string", "enum": VALID_PERIODS, "description": "Lookback window. Default 1y."},
            },
            "required": ["symbols"],
        },
    },
    {
        "name": "get_news",
        "description": "Recent news headlines for a stock from Yahoo Finance.",
        "input_schema": {
            "type": "object",
            "properties": {"symbol": _SYMBOL, "limit": {"type": "integer", "minimum": 1, "maximum": 20}},
            "required": ["symbol"],
        },
    },
]
