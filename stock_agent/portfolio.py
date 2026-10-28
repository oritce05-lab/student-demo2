"""Investor profile, portfolio tracking and monthly purchase planning.

State is kept in two JSON files under $STOCK_AGENT_HOME (default ~/.stock_agent):
  profile.json    - who the investor is and their target allocation
  portfolio.json  - cash, holdings and the transaction log
"""

from __future__ import annotations

import json
import math
import os
from datetime import date
from pathlib import Path

from . import market_data
from .market_data import ToolError, _clean

# Profile fields the agent may set, with their expected JSON types.
PROFILE_FIELDS: dict[str, type | tuple[type, ...]] = {
    "name": str,
    "age": int,
    "monthly_deposit_ils": (int, float),
    "broker": str,
    "emergency_fund_months": (int, float),
    "monthly_expenses_ils": (int, float),
    "has_pension": bool,
    "has_keren_hishtalmut": bool,
    "debts": str,
    "risk_tolerance": str,
    "goal": str,
    "horizon_years": int,
    "target_allocation": dict,
    "min_commission_ils": (int, float),
    "commission_pct": (int, float),
    "notes": str,
}

RISK_LEVELS = {"low", "medium", "high"}

# Yahoo Finance FX tickers quoting 1 unit of currency in ILS.
FX_TICKERS = {"USD": "ILS=X", "EUR": "EURILS=X", "GBP": "GBPILS=X"}


def _home() -> Path:
    path = Path(os.environ.get("STOCK_AGENT_HOME", Path.home() / ".stock_agent"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load(name: str, default: dict) -> dict:
    path = _home() / name
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save(name: str, data: dict) -> None:
    (_home() / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_profile() -> dict:
    return _load("profile.json", {})


def load_portfolio() -> dict:
    return _load("portfolio.json", {"cash_ils": 0.0, "holdings": {}, "transactions": []})


def fx_to_ils(currency: str | None) -> float:
    """How many ILS one unit of `currency` is worth. TASE quotes in agorot (ILA)."""
    if currency in (None, "ILS"):
        return 1.0
    if currency == "ILA":
        return 0.01
    if currency == "GBp":  # London quotes some funds in pence
        return fx_to_ils("GBP") / 100
    ticker = FX_TICKERS.get(currency)
    if ticker is None:
        raise ToolError(f"Unsupported currency '{currency}'.")
    return float(market_data._history(ticker, period="5d")["Close"].iloc[-1])


def price_in_ils(symbol: str) -> dict:
    ticker = market_data.yf.Ticker(symbol)
    price = float(market_data._history(symbol, period="5d")["Close"].iloc[-1])
    currency = (ticker.info or {}).get("currency")
    return {"price": price, "currency": currency, "price_ils": price * fx_to_ils(currency)}


def get_profile() -> dict:
    profile = load_profile()
    missing = [f for f in ("age", "monthly_deposit_ils", "emergency_fund_months", "risk_tolerance", "target_allocation")
               if f not in profile]
    return {"profile": profile, "missing_important_fields": missing}


def update_profile(updates: dict) -> dict:
    profile = load_profile()
    for key, value in updates.items():
        if key not in PROFILE_FIELDS:
            raise ToolError(f"Unknown profile field '{key}'. Allowed: {', '.join(PROFILE_FIELDS)}")
        expected = PROFILE_FIELDS[key]
        if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
            raise ToolError(f"Field '{key}' has the wrong type.")
        if key == "risk_tolerance" and value not in RISK_LEVELS:
            raise ToolError(f"risk_tolerance must be one of {sorted(RISK_LEVELS)}.")
        if key == "target_allocation":
            value = {s.upper().strip(): float(p) for s, p in value.items()}
            if any(p <= 0 for p in value.values()) or abs(sum(value.values()) - 100) > 0.5:
                raise ToolError("target_allocation percentages must be positive and sum to 100.")
        profile[key] = value
    _save("profile.json", profile)
    return {"saved": True, "profile": profile}


def record_transaction(type: str, total_ils: float, symbol: str | None = None, quantity: float | None = None,
                       date_str: str | None = None, note: str | None = None) -> dict:
    """Record a deposit, withdrawal, buy or sell. total_ils is what actually moved, fees included."""
    portfolio = load_portfolio()
    holdings = portfolio["holdings"]
    if total_ils <= 0:
        raise ToolError("total_ils must be positive.")
    result: dict = {}

    if type == "deposit":
        portfolio["cash_ils"] += total_ils
    elif type == "withdraw":
        portfolio["cash_ils"] -= total_ils
    elif type in ("buy", "sell"):
        if not symbol or not quantity or quantity <= 0:
            raise ToolError("buy/sell need a symbol and a positive quantity.")
        symbol = symbol.upper().strip()
        position = holdings.setdefault(symbol, {"quantity": 0.0, "cost_ils": 0.0})
        if type == "buy":
            position["quantity"] += quantity
            position["cost_ils"] += total_ils
            portfolio["cash_ils"] -= total_ils
        else:
            if quantity > position["quantity"] + 1e-9:
                raise ToolError(f"Cannot sell {quantity} {symbol}: only {position['quantity']} held.")
            cost_sold = position["cost_ils"] * quantity / position["quantity"]
            position["quantity"] -= quantity
            position["cost_ils"] -= cost_sold
            portfolio["cash_ils"] += total_ils
            result["realized_gain_ils"] = round(total_ils - cost_sold, 2)
            if position["quantity"] < 1e-9:
                del holdings[symbol]
    else:
        raise ToolError("type must be one of: deposit, withdraw, buy, sell.")

    portfolio["transactions"].append({
        "date": date_str or date.today().isoformat(), "type": type, "symbol": symbol,
        "quantity": quantity, "total_ils": total_ils, "note": note,
    })
    _save("portfolio.json", portfolio)
    return {"saved": True, "cash_ils": round(portfolio["cash_ils"], 2), **result}


def get_portfolio() -> dict:
    portfolio = load_portfolio()
    target = load_profile().get("target_allocation", {})
    positions, invested = [], 0.0
    for symbol, pos in portfolio["holdings"].items():
        try:
            quote = price_in_ils(symbol)
            value, source = pos["quantity"] * quote["price_ils"], "live (Yahoo Finance)"
        except Exception:
            if pos.get("last_value_ils") is None:
                raise
            quote = {"price": None, "currency": None}
            value, source = pos["last_value_ils"], "broker export (no live price - rename to a Yahoo ticker)"
        invested += value
        positions.append({
            "symbol": symbol, "name": pos.get("name"), "quantity": pos["quantity"], "price": _clean(quote["price"]),
            "currency": quote["currency"], "price_source": source,
            "value_ils": round(value, 2), "cost_ils": round(pos["cost_ils"], 2),
            "gain_ils": round(value - pos["cost_ils"], 2),
            "gain_pct": _clean((value / pos["cost_ils"] - 1) * 100) if pos["cost_ils"] else None,
        })
    for p in positions:
        p["allocation_pct"] = _clean(p["value_ils"] / invested * 100) if invested else None
        if p["symbol"] in target:
            p["target_pct"] = target[p["symbol"]]
    deposits = sum(t["total_ils"] for t in portfolio["transactions"] if t["type"] == "deposit")
    withdrawals = sum(t["total_ils"] for t in portfolio["transactions"] if t["type"] == "withdraw")
    return {
        "cash_ils": round(portfolio["cash_ils"], 2),
        "invested_value_ils": round(invested, 2),
        "total_value_ils": round(invested + portfolio["cash_ils"], 2),
        "net_deposits_ils": round(deposits - withdrawals, 2),
        "positions": sorted(positions, key=lambda p: -p["value_ils"]),
        "target_allocation": target,
        "recent_transactions": portfolio["transactions"][-10:],
    }


def _commission(trade_ils: float, profile: dict) -> float:
    return max(profile.get("min_commission_ils", 0.0), trade_ils * profile.get("commission_pct", 0.0) / 100)


def plan_monthly_purchase(amount_ils: float | None = None, max_commission_pct: float = 1.0) -> dict:
    """Split this month's money across the target allocation, steering toward it with new money only (no sales).

    Buys that would pay more than max_commission_pct of their size in commission are dropped and their money
    goes to the remaining, most-underweight assets. Whole units only.
    """
    profile = load_profile()
    target = profile.get("target_allocation")
    if not target:
        raise ToolError("No target_allocation in the profile yet. Agree on one with the user and save it first.")
    portfolio = load_portfolio()
    if amount_ils is None:
        amount_ils = portfolio["cash_ils"] if portfolio["cash_ils"] > 0 else profile.get("monthly_deposit_ils")
    if not amount_ils or amount_ils <= 0:
        raise ToolError("No amount to invest: pass amount_ils or record a deposit.")

    quotes = {s: price_in_ils(s) for s in target}
    values = {}
    for s, pos in portfolio["holdings"].items():
        try:
            quotes.setdefault(s, price_in_ils(s))
            values[s] = pos["quantity"] * quotes[s]["price_ils"]
        except Exception:
            if pos.get("last_value_ils") is None:
                raise
            values[s] = pos["last_value_ils"]
    total_after = sum(values.values()) + amount_ils
    deficits = {s: max(0.0, pct / 100 * total_after - values.get(s, 0.0)) for s, pct in target.items()}

    candidates = sorted(target, key=lambda s: -deficits[s])
    notes = []
    while True:
        weight = {s: deficits[s] for s in candidates}
        if sum(weight.values()) <= 0:  # already at/over target everywhere: split by target weights
            weight = {s: target[s] for s in candidates}
        total_weight = sum(weight.values())
        budget = {s: amount_ils * w / total_weight for s, w in weight.items()}
        too_costly = [s for s in candidates if _commission(budget[s], profile) > budget[s] * max_commission_pct / 100]
        if not too_costly or len(candidates) == 1:
            break
        dropped = min(too_costly, key=lambda s: deficits[s])
        candidates.remove(dropped)
        notes.append(f"Skipped {dropped} this month: commission would exceed {max_commission_pct}% of the buy.")

    orders, spent = [], 0.0
    for s in candidates:
        price = quotes[s]["price_ils"]
        units = math.floor(max(0.0, budget[s] - _commission(budget[s], profile)) / price)
        if units == 0:
            notes.append(f"{s}: budget {budget[s]:.0f} ILS is below one unit ({price:.0f} ILS).")
            continue
        cost = units * price
        fee = _commission(cost, profile)
        spent += cost + fee
        orders.append({
            "symbol": s, "units": units, "price": _clean(quotes[s]["price"]), "currency": quotes[s]["currency"],
            "price_ils": round(price, 2), "cost_ils": round(cost, 2), "est_commission_ils": round(fee, 2),
        })
    if "min_commission_ils" not in profile and "commission_pct" not in profile:
        notes.append("Commission unknown: costs assume zero fees. Save the broker's fee schedule in the profile.")
    return {
        "amount_ils": round(amount_ils, 2),
        "orders": orders,
        "estimated_total_ils": round(spent, 2),
        "left_over_ils": round(amount_ils - spent, 2),
        "notes": notes,
    }


# Column names seen in Israeli broker exports (Hebrew) and in English exports, by meaning.
IMPORT_COLUMNS = {
    "symbol": ["סימול", "symbol", "ticker"],
    "security_id": ["מספר נייר", "מס' נייר", "מס נייר", "מספר ני\"ע", "מס' ני\"ע", "security number", "security id", "isin"],
    "name": ["שם נייר", "שם הנייר", "שם ני\"ע", "שם", "name", "security name"],
    "quantity": ["כמות", "יתרה", "quantity", "shares", "units"],
    "cost_ils": ["עלות", "שווי עלות", "עלות מתואמת", "cost", "cost basis"],
    "value_ils": ["שווי שוק", "שווי", "שווי אחזקה", "market value", "value"],
}


def _match_column(columns: list[str], aliases: list[str]) -> str | None:
    normalized = {c: str(c).strip().lower() for c in columns}
    for alias in aliases:  # exact match first, then "contains", in alias priority order
        for col, norm in normalized.items():
            if norm == alias:
                return col
    for alias in aliases:
        for col, norm in normalized.items():
            if alias in norm:
                return col
    return None


def _read_table(path: Path) -> "market_data.pd.DataFrame":
    pd = market_data.pd
    if path.suffix.lower() in (".xlsx", ".xls"):
        raw = pd.read_excel(path, header=None, dtype=str)
    else:
        raw = pd.read_csv(path, header=None, dtype=str, encoding="utf-8-sig", sep=None, engine="python")
    # Exports often start with a title block; the header is the first row naming a quantity column.
    for i in range(min(20, len(raw))):
        row = [str(v) for v in raw.iloc[i].tolist() if isinstance(v, str)]
        if _match_column(row, IMPORT_COLUMNS["quantity"]):
            table = raw.iloc[i + 1:].copy()
            table.columns = [str(c).strip() for c in raw.iloc[i].tolist()]
            return table.dropna(how="all")
    raise ToolError("Could not find a header row with a quantity column (כמות / quantity) in the file.")


def _number(value) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).replace(",", "").replace("₪", "").replace("%", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def import_holdings_file(path: str) -> dict:
    """Replace current holdings with a snapshot exported from the broker (CSV or Excel)."""
    file = Path(path).expanduser()
    if not file.exists():
        raise ToolError(f"File not found: {file}")
    table = _read_table(file)
    columns = list(table.columns)
    found = {key: _match_column(columns, aliases) for key, aliases in IMPORT_COLUMNS.items()}
    if not found["symbol"] and not found["security_id"] and not found["name"]:
        raise ToolError(f"No symbol / security number / name column. Columns found: {columns}")

    holdings, skipped = {}, []
    for _, row in table.iterrows():
        quantity = _number(row[found["quantity"]])
        symbol = str(row[found["symbol"]]).strip() if found["symbol"] else ""
        security_id = str(row[found["security_id"]]).strip() if found["security_id"] else ""
        name = str(row[found["name"]]).strip() if found["name"] else ""
        if not quantity or quantity <= 0:
            skipped.append(name or symbol or security_id or "(empty row)")
            continue
        key = (symbol if symbol and symbol.lower() != "nan" else security_id or name).upper()
        holdings[key] = {
            "quantity": quantity,
            "cost_ils": (_number(row[found["cost_ils"]]) if found["cost_ils"] else None) or 0.0,
            "name": name if name.lower() != "nan" else None,
            "security_id": security_id if security_id.lower() != "nan" else None,
            "last_value_ils": _number(row[found["value_ils"]]) if found["value_ils"] else None,
        }

    portfolio = load_portfolio()
    portfolio["holdings"] = holdings
    portfolio["transactions"].append({"date": date.today().isoformat(), "type": "import", "symbol": None,
                                      "quantity": None, "total_ils": None, "note": f"Imported {file.name}"})
    _save("portfolio.json", portfolio)
    needs_ticker = [k for k in holdings if k.isdigit()]
    return {
        "imported": len(holdings),
        "columns_used": {k: v for k, v in found.items() if v},
        "holdings": holdings,
        "skipped_rows": skipped[:20],
        "needs_yahoo_ticker": needs_ticker,
    }


def rename_holding(old_symbol: str, new_symbol: str) -> dict:
    """Point a holding at its Yahoo Finance ticker (e.g. a TASE security number -> 'TA35.TA')."""
    portfolio = load_portfolio()
    old_symbol, new_symbol = old_symbol.upper().strip(), new_symbol.upper().strip()
    if old_symbol not in portfolio["holdings"]:
        raise ToolError(f"No holding named '{old_symbol}'.")
    if new_symbol in portfolio["holdings"]:
        raise ToolError(f"'{new_symbol}' already exists in the portfolio.")
    portfolio["holdings"][new_symbol] = portfolio["holdings"].pop(old_symbol)
    _save("portfolio.json", portfolio)
    return {"saved": True, "symbol": new_symbol}


TOOLS = {
    "import_holdings_file": import_holdings_file,
    "rename_holding": rename_holding,
    "get_profile": get_profile,
    "update_profile": update_profile,
    "record_transaction": record_transaction,
    "get_portfolio": get_portfolio,
    "plan_monthly_purchase": plan_monthly_purchase,
}

TOOL_DEFINITIONS = [
    {
        "name": "import_holdings_file",
        "description": "Load the user's real holdings from a file exported from their broker's website (CSV or Excel, "
                       "Hebrew or English columns). Replaces the stored holdings with this snapshot.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Path to the exported .xlsx/.xls/.csv file."}},
            "required": ["path"],
        },
    },
    {
        "name": "rename_holding",
        "description": "Change a holding's key to its Yahoo Finance ticker so live prices work - e.g. after an import "
                       "keyed by a TASE security number, find the ticker (web_search) and rename it.",
        "input_schema": {
            "type": "object",
            "properties": {"old_symbol": {"type": "string"}, "new_symbol": {"type": "string"}},
            "required": ["old_symbol", "new_symbol"],
        },
    },
    {
        "name": "get_profile",
        "description": "Read the investor's saved profile (age, monthly deposit, safety net, risk tolerance, goals, "
                       "target allocation, broker commissions) and which important fields are still missing.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "update_profile",
        "description": "Save facts the user told you about themselves, or an agreed target allocation. Only save what "
                       "the user stated or explicitly agreed to. target_allocation maps ticker -> percent (sums to 100).",
        "input_schema": {
            "type": "object",
            "properties": {
                "updates": {
                    "type": "object",
                    "description": "Fields to set: " + ", ".join(PROFILE_FIELDS)
                                   + ". risk_tolerance is low/medium/high. commission_pct is a percent (0.1 = 0.1%).",
                },
            },
            "required": ["updates"],
        },
    },
    {
        "name": "record_transaction",
        "description": "Log a deposit, withdrawal, buy or sell the user ACTUALLY executed at their broker. Never log "
                       "a planned trade. total_ils is the amount that moved in shekels, commission included.",
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["deposit", "withdraw", "buy", "sell"]},
                "total_ils": {"type": "number"},
                "symbol": {"type": "string"},
                "quantity": {"type": "number"},
                "date_str": {"type": "string", "description": "YYYY-MM-DD; defaults to today."},
                "note": {"type": "string"},
            },
            "required": ["type", "total_ils"],
        },
    },
    {
        "name": "get_portfolio",
        "description": "Current holdings valued in ILS at live prices, gains, cash, and allocation vs. target.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "plan_monthly_purchase",
        "description": "Concrete buy orders for this month's money: moves the portfolio toward the target allocation "
                       "with new money only, whole units, and skips buys whose commission is too large a share.",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount_ils": {"type": "number", "description": "Defaults to available cash, else the monthly deposit."},
                "max_commission_pct": {"type": "number", "description": "Max commission as % of a buy. Default 1."},
            },
        },
    },
]
