"""Command line.

  python -m stock_agent                     chat with the advisor
  python -m stock_agent "question"          one question
  python -m stock_agent import FILE         load holdings from a broker export (CSV / Excel)
  python -m stock_agent monitor             one alert pass (run every ~15 min from cron / GitHub Actions)
  python -m stock_agent report              build and email the weekly report
  python -m stock_agent status              check the setup

monitor/report accept --dry-run (no email; saved to the outbox) and monitor accepts --force (ignore market hours).
Output is counts only, so it is safe for public CI logs.
"""

from __future__ import annotations

import json
import os
import sys

from .agent import main as chat, run_tool
from .config import email_settings, sec_user_agent
from .portfolio import _home, load_portfolio


def status() -> dict:
    from . import markets

    holdings = list(load_portfolio()["holdings"])
    email = email_settings()
    return {
        "data_dir": str(_home()),
        "holdings": len(holdings),
        "holdings_without_yahoo_ticker": sum(1 for h in holdings if h.isdigit()),
        "email_configured": all(email[k] for k in ("user", "password", "to")),
        "claude_configured": bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")),
        "sec_filings_enabled": bool(sec_user_agent()),
        "markets_open_now": sorted({markets.market_of(s) for s in holdings if markets.is_open(s)}),
    }


def main() -> None:
    args = sys.argv[1:]
    command = args[0] if args else None
    flags = set(args[1:])

    if command == "import" and len(args) > 1:
        content, is_error = run_tool("import_holdings_file", {"path": args[1]})
        if "--quiet" in flags:
            print("import failed" if is_error else f"imported {json.loads(content)['imported']} holdings")
        else:
            print(content)
        sys.exit(1 if is_error else 0)
    if command == "monitor":
        from .monitor import run_monitor

        print(json.dumps(run_monitor(dry_run="--dry-run" in flags, force="--force" in flags)))
        return
    if command == "report":
        from .report import run_weekly_report

        print(json.dumps(run_weekly_report(dry_run="--dry-run" in flags), ensure_ascii=False))
        return
    if command == "status":
        print(json.dumps(status(), indent=2))
        return
    chat()
