import numpy as np
import pandas as pd
import pytest

from stock_agent import market_data
from stock_agent.agent import run_tool


class FakeTicker:
    def __init__(self, symbol):
        self.symbol = symbol
        self.info = {"longName": f"{symbol} Inc.", "currency": "USD", "marketCap": 1e12, "trailingPE": 25.0}
        self.news = [{"content": {"title": "Headline", "provider": {"displayName": "Reuters"},
                                  "pubDate": "2026-10-27", "canonicalUrl": {"url": "https://example.com"}}}]

    def history(self, period, interval, auto_adjust):
        if self.symbol == "BAD":
            return pd.DataFrame()
        days = {"5d": 5, "6mo": 126, "1y": 252, "2y": 504}.get(period, 252)
        idx = pd.bdate_range(end="2026-10-27", periods=days, tz="America/New_York")
        rng = np.random.default_rng(len(self.symbol))
        close = 100 * np.cumprod(1 + rng.normal(0.0005, 0.01, days))
        return pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close,
                             "Volume": 1_000_000}, index=idx)


@pytest.fixture(autouse=True)
def fake_yf(monkeypatch):
    monkeypatch.setattr(market_data.yf, "Ticker", FakeTicker)


def test_quote():
    q = market_data.get_quote("aapl")
    assert q["symbol"] == "AAPL" and q["price"] > 0 and q["name"] == "AAPL Inc."


def test_history_is_sampled():
    h = market_data.get_price_history("AAPL", period="2y")
    assert len(h["closes"]) <= market_data.MAX_HISTORY_ROWS
    assert h["closes"][-1]["date"] == h["end"]


def test_technical_indicators():
    t = market_data.get_technical_indicators("NVDA")
    assert t["sma_200"] is not None and 0 <= t["rsi_14"] <= 100 and t["signals"]


def test_compare():
    c = market_data.compare_stocks(["AAPL", "MSFT", "TEVA.TA"])
    assert len(c["stocks"]) == 3
    assert c["daily_return_correlation"]["AAPL"]["AAPL"] == pytest.approx(1.0)


def test_news():
    assert market_data.get_news("AAPL")["news"][0]["publisher"] == "Reuters"


def test_run_tool_errors_are_reported():
    content, is_error = run_tool("get_quote", {"symbol": "BAD"})
    assert is_error and "No price data" in content
    assert run_tool("get_price_history", {"symbol": "AAPL", "period": "7y"})[1]
    assert run_tool("get_quote", {"ticker": "AAPL"})[1]
    assert run_tool("nope", {})[1]
    assert not run_tool("get_quote", {"symbol": "AAPL"})[1]
