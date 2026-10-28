import math

import pandas as pd
import pytest

from stock_agent import indicators


def series(values):
    return pd.Series(values, dtype=float)


def test_sma():
    out = indicators.sma(series([1, 2, 3, 4, 5]), 3)
    assert math.isnan(out.iloc[1])
    assert out.iloc[-1] == pytest.approx(4.0)


def test_rsi_all_gains_is_100():
    assert indicators.rsi(series(range(1, 40))).iloc[-1] == pytest.approx(100.0)


def test_rsi_all_losses_is_0():
    assert indicators.rsi(series(range(40, 1, -1))).iloc[-1] == pytest.approx(0.0)


def test_rsi_bounded():
    prices = series([10, 11, 10.5, 12, 11, 13, 12.5, 14, 13, 15, 14, 16, 15, 17, 16, 18, 17])
    value = indicators.rsi(prices).iloc[-1]
    assert 0 < value < 100


def test_macd_flat_series_is_zero():
    out = indicators.macd(series([50] * 60)).iloc[-1]
    assert out["macd"] == pytest.approx(0.0)
    assert out["histogram"] == pytest.approx(0.0)


def test_bollinger_bands_order():
    prices = series([10, 12, 11, 13, 12, 14, 13, 15, 14, 16, 15, 17, 16, 18, 17, 19, 18, 20, 19, 21])
    band = indicators.bollinger_bands(prices).iloc[-1]
    assert band["lower"] < band["middle"] < band["upper"]


def test_max_drawdown():
    assert indicators.max_drawdown(series([100, 120, 90, 110])) == pytest.approx(-0.25)


def test_total_return():
    assert indicators.total_return(series([100, 150])) == pytest.approx(0.5)


def test_volatility_zero_for_constant_growth():
    assert indicators.annualized_volatility(series([100 * 1.01**i for i in range(30)])) == pytest.approx(0.0, abs=1e-12)
