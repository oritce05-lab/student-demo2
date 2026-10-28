"""Which exchange a holding trades on, and whether it is open right now.

Uses exchange_calendars, which knows each exchange's sessions, holidays, half days and
daylight-saving changes (including TASE's Monday-Friday week).
"""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

import exchange_calendars as xcals
import pandas as pd

SUFFIX_CALENDARS = {".TA": "XTAE", ".L": "XLON"}
MARKET_NAMES = {"XTAE": "Israel", "XNYS": "US", "XLON": "London"}


def calendar_code(symbol: str) -> str:
    symbol = symbol.upper()
    for suffix, code in SUFFIX_CALENDARS.items():
        if symbol.endswith(suffix):
            return code
    if symbol.isdigit():  # TASE security number from a broker export
        return "XTAE"
    return "XNYS"


def market_of(symbol: str) -> str:
    return MARKET_NAMES[calendar_code(symbol)]


@lru_cache(maxsize=None)
def _calendar(code: str):
    return xcals.get_calendar(code)


def _minute(now: datetime | None) -> pd.Timestamp:
    ts = pd.Timestamp(now or datetime.now(timezone.utc))
    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
    return ts.floor("min")


def is_open(symbol: str, now: datetime | None = None) -> bool:
    calendar = _calendar(calendar_code(symbol))
    minute = _minute(now)
    if not calendar.first_minute <= minute <= calendar.last_minute:
        return False
    return bool(calendar.is_open_on_minute(minute))


def any_open(symbols, now: datetime | None = None) -> bool:
    return any(is_open(s, now) for s in symbols)
