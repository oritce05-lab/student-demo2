from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from stock_agent import ai, market_data, monitor, portfolio, report

OPEN_BOTH = datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc)   # TASE and NYSE open
CLOSED = datetime(2026, 11, 7, 15, 0, tzinfo=timezone.utc)      # Saturday


class FakeTicker:
    moves = {"AAPL": 0.12, "TEVA.TA": 0.01}  # today's move vs previous close

    def __init__(self, symbol):
        self.symbol = symbol
        last, prev = self._closes()[-1], self._closes()[-2]
        currency = {"TEVA.TA": "ILA", "ILS=X": "ILS"}.get(symbol, "USD")
        self.info = {"longName": f"{symbol} Co", "currency": currency, "quoteType": "EQUITY",
                     "sector": "Technology" if symbol == "AAPL" else "Healthcare",
                     "regularMarketPrice": last, "regularMarketPreviousClose": prev,
                     "regularMarketTime": int(OPEN_BOTH.timestamp()), "fiftyTwoWeekHigh": last * 1.05}
        self.calendar = {}

    def _closes(self):
        base = {"AAPL": 200.0, "TEVA.TA": 6000.0, "ILS=X": 3.7}.get(self.symbol, 100.0)
        closes = list(base * (1 + 0.001 * np.arange(60)))
        closes[-1] = closes[-2] * (1 + self.moves.get(self.symbol, 0))
        return closes

    def history(self, period=None, interval="1d", auto_adjust=True, start=None, end=None):
        closes = self._closes()
        idx = pd.bdate_range(end="2026-11-02", periods=len(closes))
        return pd.DataFrame({"Open": closes, "High": closes, "Low": closes, "Close": closes, "Volume": 1}, index=idx)


@pytest.fixture(autouse=True)
def setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STOCK_AGENT_HOME", str(tmp_path))
    for var in ("SMTP_USER", "SMTP_PASSWORD", "ALERT_EMAIL_TO", "SEC_USER_AGENT", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(market_data.yf, "Ticker", FakeTicker)
    portfolio.record_transaction("buy", 7000, symbol="AAPL", quantity=10)
    portfolio.record_transaction("buy", 6000, symbol="TEVA.TA", quantity=100)


def test_price_alert_sent_once_and_only_when_open(tmp_path):
    assert monitor.run_monitor(now=CLOSED)["status"] == "markets closed"
    first = monitor.run_monitor(now=OPEN_BOTH)
    assert first["alerts"] >= 1 and first["email"] == "outbox"
    outbox = list((tmp_path / "outbox").glob("*.html"))
    assert any("AAPL" in f.read_text(encoding="utf-8") for f in outbox)
    assert monitor.run_monitor(now=OPEN_BOTH)["alerts"] == 0  # no duplicate


def test_unverified_move_is_not_alerted(monkeypatch):
    original = FakeTicker.__init__

    def mismatched(self, symbol):
        original(self, symbol)
        self.info["regularMarketPreviousClose"] = self.info["regularMarketPrice"] / 1.30  # quote says +30%

    monkeypatch.setattr(FakeTicker, "__init__", mismatched)
    monkeypatch.setattr(FakeTicker, "moves", {"AAPL": 0.0})
    result = monitor.run_monitor(now=OPEN_BOTH)
    log = monitor.load_state()["log"]
    assert any(e["status"] == "unverified" for e in log)
    assert not any(e["kind"] == "price" and e["status"] == "outbox" for e in log)


def test_weekly_report_renders_without_ai(tmp_path):
    result = report.run_weekly_report(now=OPEN_BOTH)
    assert result["status"] == "report created" and not result["ai_sections"]
    page = (tmp_path / "reports" / "weekly-2026-11-02.html").read_text(encoding="utf-8")
    assert "תמונת מצב" in page and "AAPL" in page and "מגבלות הנתונים" in page
    assert not ai.available()
