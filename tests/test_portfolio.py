import pandas as pd
import pytest

from stock_agent import market_data, portfolio
from stock_agent.market_data import ToolError

PRICES = {"CSPX.L": (500.0, "USD"), "TA35.TA": (2000.0, "ILA"), "ILS=X": (3.7, "ILS")}


class FakeTicker:
    def __init__(self, symbol):
        self.symbol = symbol
        self.info = {"currency": PRICES.get(symbol, (0, None))[1]}

    def history(self, period, interval, auto_adjust):
        if self.symbol not in PRICES:
            return pd.DataFrame()
        idx = pd.bdate_range(end="2026-10-27", periods=5)
        return pd.DataFrame({"Close": [PRICES[self.symbol][0]] * 5}, index=idx)


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("STOCK_AGENT_HOME", str(tmp_path))
    monkeypatch.setattr(market_data.yf, "Ticker", FakeTicker)


def test_profile_validation():
    portfolio.update_profile({"age": 47, "monthly_deposit_ils": 1500, "broker": "Excellence Trade"})
    assert portfolio.get_profile()["profile"]["age"] == 47
    with pytest.raises(ToolError):
        portfolio.update_profile({"target_allocation": {"CSPX.L": 50, "TA35.TA": 40}})
    with pytest.raises(ToolError):
        portfolio.update_profile({"favorite_color": "blue"})
    with pytest.raises(ToolError):
        portfolio.update_profile({"age": "47"})


def test_price_in_ils_converts_currencies():
    assert portfolio.price_in_ils("CSPX.L")["price_ils"] == pytest.approx(1850.0)
    assert portfolio.price_in_ils("TA35.TA")["price_ils"] == pytest.approx(20.0)  # agorot -> shekels


def test_transactions_and_portfolio_value():
    portfolio.record_transaction("deposit", 5000)
    portfolio.record_transaction("buy", 3720, symbol="CSPX.L", quantity=2)
    result = portfolio.record_transaction("sell", 1900, symbol="CSPX.L", quantity=1)
    assert result["realized_gain_ils"] == pytest.approx(40.0)
    with pytest.raises(ToolError):
        portfolio.record_transaction("sell", 100, symbol="CSPX.L", quantity=5)
    snap = portfolio.get_portfolio()
    assert snap["cash_ils"] == pytest.approx(3180.0)
    assert snap["positions"][0]["value_ils"] == pytest.approx(1850.0)
    assert snap["total_value_ils"] == pytest.approx(5030.0)


def test_plan_steers_new_money_to_underweight_asset():
    portfolio.update_profile({"monthly_deposit_ils": 1500, "target_allocation": {"CSPX.L": 50, "TA35.TA": 50}})
    portfolio.record_transaction("buy", 3700, symbol="CSPX.L", quantity=2)  # 3700 ILS already in CSPX
    plan = portfolio.plan_monthly_purchase(1500)
    assert [o["symbol"] for o in plan["orders"]] == ["TA35.TA"]
    assert plan["orders"][0]["units"] == 75  # 1500 / 20 ILS
    assert any("Commission unknown" in n for n in plan["notes"])


def test_plan_skips_buys_where_commission_is_too_high():
    portfolio.update_profile({"min_commission_ils": 15.0, "target_allocation": {"CSPX.L": 50, "TA35.TA": 50}})
    plan = portfolio.plan_monthly_purchase(1500)  # 750 each -> 2% commission; consolidate into one
    assert len(plan["orders"]) == 1
    assert any("Skipped" in n for n in plan["notes"])


def test_plan_requires_target():
    with pytest.raises(ToolError):
        portfolio.plan_monthly_purchase(1500)


def test_import_hebrew_excel_export(tmp_path):
    path = tmp_path / "export.xlsx"
    rows = [
        ["דוח אחזקות", None, None, None, None],
        [None, None, None, None, None],
        ["שם נייר", "מספר נייר", "כמות", "שווי שוק", "עלות"],
        ["תכלית ת\"א 35", "1143718", "10", "2,050.5", "1,900"],
        ["סה\"כ", None, None, "2,050.5", None],
    ]
    pd.DataFrame(rows).to_excel(path, header=False, index=False)
    result = portfolio.import_holdings_file(str(path))
    assert result["imported"] == 1 and result["needs_yahoo_ticker"] == ["1143718"]
    holding = result["holdings"]["1143718"]
    assert holding["quantity"] == 10 and holding["cost_ils"] == 1900 and holding["last_value_ils"] == 2050.5

    snap = portfolio.get_portfolio()  # no live price for a security number -> broker value
    assert snap["positions"][0]["value_ils"] == pytest.approx(2050.5)
    assert snap["positions"][0]["price_source"].startswith("broker export")

    portfolio.rename_holding("1143718", "TA35.TA")
    assert portfolio.get_portfolio()["positions"][0]["value_ils"] == pytest.approx(200.0)


def test_import_english_csv(tmp_path):
    path = tmp_path / "export.csv"
    path.write_text("Symbol,Name,Quantity,Market Value\nCSPX.L,iShares S&P 500,3,5550\n", encoding="utf-8")
    result = portfolio.import_holdings_file(str(path))
    assert result["holdings"]["CSPX.L"]["quantity"] == 3
