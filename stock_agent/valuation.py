"""Value the portfolio: live prices, verified daily moves, ILS/USD values and returns.

Every figure carries its source and timestamp. When cost data is missing, returns are left
as None and the gap is listed in `limitations` rather than guessed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import market_data, markets
from .market_data import _clean
from .portfolio import FX_TICKERS, fx_to_ils, load_portfolio

SOURCE = "Yahoo Finance"


def _info(symbol: str) -> dict:
    return market_data.yf.Ticker(symbol).info or {}


def fx_on(currency: str | None, day: str) -> float:
    """ILS per unit of `currency` at the close on or before `day` (YYYY-MM-DD)."""
    if currency in (None, "ILS", "ILA"):
        return fx_to_ils(currency)
    base = "GBP" if currency == "GBp" else currency
    end = datetime.fromisoformat(day) + timedelta(days=1)
    df = market_data.yf.Ticker(FX_TICKERS[base]).history(start=end - timedelta(days=10), end=end, auto_adjust=False)
    if df.empty:
        raise market_data.ToolError(f"No {base}/ILS rate for {day}.")
    rate = float(df["Close"].iloc[-1])
    return rate / 100 if currency == "GBp" else rate


def quote(symbol: str, tolerance_pct: float = 1.0) -> dict:
    """Current price and daily change, cross-checked between Yahoo's quote and its daily bars."""
    info = _info(symbol)
    bars = market_data._history(symbol, period="5d", auto_adjust=False)["Close"]
    bar_change = (bars.iloc[-1] / bars.iloc[-2] - 1) * 100 if len(bars) > 1 else None

    price, prev = info.get("regularMarketPrice"), info.get("regularMarketPreviousClose")
    quote_change = (price / prev - 1) * 100 if price and prev else None
    if quote_change is None:  # fall back to the bars alone; unverified
        price, prev = float(bars.iloc[-1]), (float(bars.iloc[-2]) if len(bars) > 1 else None)
    verified = quote_change is not None and bar_change is not None and abs(quote_change - bar_change) <= tolerance_pct

    as_of = info.get("regularMarketTime")
    return {
        "symbol": symbol,
        "name": info.get("longName") or info.get("shortName") or symbol,
        "currency": info.get("currency"),
        "price": float(price),
        "previous_close": float(prev) if prev else None,
        "change_pct": quote_change if quote_change is not None else bar_change,
        "verified": verified,
        "as_of": datetime.fromtimestamp(as_of, timezone.utc).isoformat(timespec="minutes") if as_of else
                 bars.index[-1].strftime("%Y-%m-%d"),
        "delay_minutes": info.get("exchangeDataDelayedBy"),
        "source": SOURCE,
        "quote_type": info.get("quoteType"),
        "sector": info.get("sector") or (f"ETF: {info['category']}" if info.get("category") else None),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
    }


def value_portfolio(tolerance_pct: float = 1.0) -> dict:
    portfolio = load_portfolio()
    usd_ils = fx_to_ils("USD")
    positions, failures, limitations = [], [], []

    for symbol, holding in portfolio["holdings"].items():
        qty = holding["quantity"]
        base = {"symbol": symbol, "name": holding.get("name") or symbol, "quantity": qty,
                "market": markets.market_of(symbol), "purchase_date": holding.get("purchase_date")}
        try:
            q = quote(symbol, tolerance_pct)
        except Exception as e:  # no live price (bad ticker, provider down)
            failures.append({"symbol": symbol, "error": type(e).__name__})
            if holding.get("last_value_ils") is not None:
                positions.append({**base, "value_ils": holding["last_value_ils"], "price_source": "broker export",
                                  "value_usd": holding["last_value_ils"] / usd_ils, "live": False})
                limitations.append(f"{symbol}: אין מחיר חי, מוצג השווי מקובץ הברוקר.")
            continue

        fx = fx_to_ils(q["currency"])
        value_native = qty * q["price"]
        position = {
            **base, **q, "name": holding.get("name") or q["name"], "live": True,
            "fx_to_ils": fx, "value_native": value_native, "value_ils": value_native * fx,
            "value_usd": value_native * fx / usd_ils,
            "day_change_ils": qty * (q["price"] - q["previous_close"]) * fx if q["previous_close"] else None,
            "is_etf": q["quote_type"] == "ETF",
        }

        # Returns since purchase: in the security's currency, and in shekels including the FX move.
        cost_native = qty * holding["avg_price"] if holding.get("avg_price") else None
        cost_ils = holding.get("cost_ils") or None
        if cost_ils is None and cost_native and holding.get("purchase_date"):
            try:
                cost_ils = cost_native * fx_on(q["currency"], holding["purchase_date"])
            except Exception:
                pass
        position["cost_ils"] = cost_ils
        position["return_native_pct"] = (value_native / cost_native - 1) * 100 if cost_native else None
        position["return_ils_pct"] = (position["value_ils"] / cost_ils - 1) * 100 if cost_ils else None
        position["gain_ils"] = position["value_ils"] - cost_ils if cost_ils else None
        if cost_ils is None:
            limitations.append(f"{symbol}: חסרים נתוני עלות, לכן אין חישוב רווח/הפסד.")
        elif cost_native is None and q["currency"] not in ("ILS", "ILA"):
            limitations.append(f"{symbol}: חסר שער קנייה במטבע המקור, לכן אין הפרדה בין תשואת המניה להשפעת המטבע.")
        if not q["verified"]:
            limitations.append(f"{symbol}: מקורות המחיר לא תאמו או חסרו - השינוי היומי לא אומת.")
        positions.append(position)

    total_ils = sum(p["value_ils"] for p in positions)
    for p in positions:
        p["weight_pct"] = p["value_ils"] / total_ils * 100 if total_ils else 0.0
    cash = portfolio.get("cash_ils", 0.0)
    if not portfolio["transactions"] or not any(t["type"] == "deposit" for t in portfolio["transactions"]):
        limitations.append("יתרת המזומן בתיק לא ידועה; השווי כולל רק ניירות ערך.")
    return {
        "as_of": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "usd_ils": usd_ils,
        "positions": sorted(positions, key=lambda p: -p["value_ils"]),
        "securities_value_ils": total_ils,
        "cash_ils": cash,
        "total_value_ils": total_ils + cash,
        "total_value_usd": (total_ils + cash) / usd_ils,
        "failures": failures,
        "limitations": limitations,
    }


def exposures(valuation: dict) -> dict:
    """Weights by market, currency and sector, plus single-stock concentration."""
    by_market, by_currency, by_sector = {}, {}, {}
    total = valuation["securities_value_ils"] or 1.0
    for p in valuation["positions"]:
        w = p["value_ils"] / total * 100
        by_market[p["market"]] = by_market.get(p["market"], 0) + w
        currency = {"ILA": "ILS", "GBp": "GBP"}.get(p.get("currency"), p.get("currency") or "ILS")
        by_currency[currency] = by_currency.get(currency, 0) + w
        sector = p.get("sector") or "לא ידוע"
        by_sector[sector] = by_sector.get(sector, 0) + w
    return {
        "by_market": {k: _clean(v) for k, v in by_market.items()},
        "by_currency": {k: _clean(v) for k, v in by_currency.items()},
        "by_sector": {k: _clean(v) for k, v in sorted(by_sector.items(), key=lambda kv: -kv[1])},
        "largest_single_stocks": [
            {"symbol": p["symbol"], "weight_pct": _clean(p["weight_pct"])}
            for p in valuation["positions"] if not p.get("is_etf")
        ][:5],
    }
