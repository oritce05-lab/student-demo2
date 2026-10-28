"""Monitoring settings. Defaults below; override in $STOCK_AGENT_HOME/config.json.

Secrets (email password, API keys) never go in config.json - they come from environment variables.
"""

from __future__ import annotations

import copy
import os

from .portfolio import _load

MODEL = "claude-opus-5-5"

DEFAULTS = {
    "investor": {"experience": "beginner", "horizon": "5+ years", "risk_tolerance": "medium",
                 "markets": ["US", "Israel"]},
    # Price alerts: daily move vs. previous close.
    "alert_threshold_pct": 10.0,
    "realert_step_pct": 5.0,          # alert again the same day only if the move grows by this much more
    "verify_tolerance_pct": 1.0,      # two price sources must agree within this many points
    # Portfolio risk alerts.
    "concentration_limit_pct": 25.0,  # single stock (not broad ETFs) as % of portfolio
    "sector_limit_pct": 40.0,
    "market_shift_pct": 10.0,         # change in Israel/US split vs. last weekly snapshot
    "drawdown_alert_pct": 20.0,       # below 52-week high, or below purchase price
    "fx_weekly_alert_pct": 3.0,       # USD/ILS move over 5 trading days
    "data_failure_runs": 4,           # consecutive failed runs before emailing about a data problem
    "benchmarks": {"S&P 500": "^GSPC", "ת\"א-125": "^TA125.TA"},
    "ai_explanations": True,          # use Claude + web search to explain moves and write the weekly report
}


def load_config() -> dict:
    config = copy.deepcopy(DEFAULTS)
    config.update(_load("config.json", {}))
    return config


def email_settings() -> dict:
    return {
        "host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER"),
        "password": os.environ.get("SMTP_PASSWORD"),
        "sender": os.environ.get("EMAIL_FROM") or os.environ.get("SMTP_USER"),
        "to": os.environ.get("ALERT_EMAIL_TO"),
    }


def sec_user_agent() -> str | None:
    """SEC requires a User-Agent naming who is calling, e.g. 'Jane Doe jane@example.com'."""
    return os.environ.get("SEC_USER_AGENT")
