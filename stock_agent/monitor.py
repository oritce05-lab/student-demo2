"""The alert engine. Meant to run every ~15 minutes (cron / GitHub Actions); it decides itself
whether a market is open.

- Price alerts: a holding's verified daily move reaches the threshold (default 10%), only while its market is open.
- Material events: new SEC filings for US holdings are recorded whenever found and emailed in the next open window.
- Risk alerts: concentration, sector, market split, currency and drawdowns, checked once per trading day.
- Every alert is logged; the same alert is not sent twice unless it got materially worse.
"""

from __future__ import annotations

import html
import math
from datetime import datetime, timedelta, timezone

from . import ai, market_data, markets, sec
from .config import load_config, sec_user_agent
from .notify import log_error, send_email
from .portfolio import _load, _save, load_portfolio
from .valuation import exposures, value_portfolio

STATE_FILE = "alerts.json"
MAX_LOG = 1000


def load_state() -> dict:
    state = _load(STATE_FILE, {})
    for key, default in (("sent", {}), ("pending", []), ("seen_filings", []), ("log", []),
                         ("failures", 0), ("failure_notified", False)):
        state.setdefault(key, default)
    return state


def _log(state: dict, now: datetime, kind: str, symbol: str | None, title: str, status: str) -> None:
    state["log"].append({"time": now.isoformat(timespec="minutes"), "kind": kind, "symbol": symbol,
                         "title": title, "status": status})
    state["log"] = state["log"][-MAX_LOG:]


def _fmt_money(value: float | None, symbol: str = "₪") -> str:
    return "—" if value is None else f"{value:,.0f} {symbol}"


def _fmt_pct(value: float | None) -> str:
    return "—" if value is None else f"{value:+.1f}%"


# ---------- price alerts ----------

def price_alerts(valuation: dict, config: dict, state: dict, open_symbols: set[str], now: datetime) -> list[dict]:
    threshold, step = config["alert_threshold_pct"], config["realert_step_pct"]
    alerts = []
    for p in valuation["positions"]:
        change = p.get("change_pct")
        if not p.get("live") or p["symbol"] not in open_symbols or change is None or abs(change) < threshold:
            continue
        if not p["verified"]:
            _log(state, now, "price", p["symbol"], f"שינוי של {change:+.1f}% לא אומת - ייבדק שוב", "unverified")
            continue
        key = f"price:{p['symbol']}:{p['as_of'][:10]}"
        level = math.floor((abs(change) - threshold) / step)
        direction = 1 if change > 0 else -1
        previous = state["sent"].get(key)
        if previous and previous["level"] >= level and previous.get("direction") == direction:
            continue  # already told her about this move
        update = " (עדכון: התנועה התרחבה)" if previous else ""
        delay = f", מעוכב בכ-{p['delay_minutes']} דקות" if p.get("delay_minutes") else ""
        impact = p.get("day_change_ils")
        impact_pct = impact / valuation["total_value_ils"] * 100 if impact and valuation["total_value_ils"] else None
        explanation = ai.explain_move(p) if config["ai_explanations"] else None
        body = f"""
<p><strong>{html.escape(p['name'])} ({p['symbol']})</strong> {'עלתה' if change > 0 else 'ירדה'} היום
<strong>{_fmt_pct(change)}</strong>{update}.</p>
<ul>
<li>מחיר סגירה קודם: {p['previous_close']:,.2f} {p['currency']} | מחיר עדכני: {p['price']:,.2f} {p['currency']}</li>
<li>מועד המחיר: {p['as_of']} UTC (מקור: {p['source']}{delay})</li>
<li>השפעה על ההחזקה: {_fmt_money(impact)} ({_fmt_pct(impact_pct)} משווי התיק). משקל המניה בתיק: {p['weight_pct']:.1f}%</li>
<li><a href="https://finance.yahoo.com/quote/{p['symbol']}">דף המניה ב-Yahoo Finance</a></li>
</ul>
<h3>הסבר אפשרי</h3>
{explanation or '<p>לא נמצא הסבר אמין באופן אוטומטי. כדאי לבדוק דיווחים רשמיים (SEC / מאיה) לפני שמסיקים מסקנות.</p>'}
<p><em>תנודה חדה לבדה איננה סיבה למכור או לקנות. כדאי לבדוק אם השתנה משהו מהותי בחברה.</em></p>"""
        alerts.append({"key": key, "level": level, "direction": direction, "kind": "price", "symbol": p["symbol"],
                       "title": f"{p['symbol']} {_fmt_pct(change)} היום", "body": body})
    return alerts


# ---------- material events ----------

def collect_filings(state: dict, now: datetime) -> None:
    """Queue new SEC filings for US holdings. Runs at most hourly, at any time of day."""
    user_agent = sec_user_agent()
    last = state.get("last_filings_check")
    if not user_agent or (last and now - datetime.fromisoformat(last) < timedelta(minutes=55)):
        return
    state["last_filings_check"] = now.isoformat(timespec="minutes")
    for symbol, holding in load_portfolio()["holdings"].items():
        if markets.market_of(symbol) != "US":
            continue
        try:
            filings = sec.recent_filings(symbol, user_agent)
        except Exception as e:
            log_error(f"SEC check failed for {symbol}", e)
            continue
        for f in filings:
            if f["accession"] in state["seen_filings"]:
                continue
            state["seen_filings"].append(f["accession"])
            name = html.escape(holding.get("name") or symbol)
            state["pending"].append({
                "key": f"filing:{f['accession']}", "kind": "event", "symbol": symbol,
                "title": f"{symbol}: {f['description']}",
                "body": f"""<p><strong>{name} ({symbol})</strong> פרסמה דיווח רשמי ל-SEC:
<strong>{html.escape(f['description'])}</strong> (טופס {f['form']}, תאריך הגשה {f['date']}).</p>
<p><a href="{f['url']}">לדיווח המלא באתר ה-SEC</a></p>
<p><em>דיווח כזה עשוי להשפיע על המניה גם אם המחיר עדיין לא זז. כדאי לקרוא את תקציר הדיווח.</em></p>""",
                "detected": now.isoformat(timespec="minutes"),
            })
            _log(state, now, "event", symbol, f["description"], "queued")
    state["seen_filings"] = state["seen_filings"][-2000:]


def due_events(state: dict, open_symbols: set[str]) -> list[dict]:
    due = [e for e in state["pending"] if e["symbol"] in open_symbols]
    state["pending"] = [e for e in state["pending"] if e["symbol"] not in open_symbols]
    return due


# ---------- risk alerts ----------

def risk_findings(valuation: dict, config: dict, state: dict) -> list[dict]:
    findings = []
    exp = exposures(valuation)

    def add(key, value, title, body):
        findings.append({"key": key, "level": int(abs(value) // 5), "kind": "risk", "symbol": None,
                         "title": title, "body": body})

    for p in valuation["positions"]:
        if p.get("live") and not p.get("is_etf") and p["weight_pct"] > config["concentration_limit_pct"]:
            add(f"risk:concentration:{p['symbol']}", p["weight_pct"], f"ריכוזיות: {p['symbol']} היא {p['weight_pct']:.0f}% מהתיק",
                f"<p>מניה בודדת, {html.escape(p['name'])}, מהווה {p['weight_pct']:.1f}% מהתיק "
                f"(הסף שהוגדר: {config['concentration_limit_pct']:.0f}%). ירידה חדה בה תשפיע מאוד על כל התיק.</p>")
        high = p.get("fifty_two_week_high")
        if p.get("live") and high:
            drop = (p["price"] / high - 1) * 100
            if drop <= -config["drawdown_alert_pct"]:
                add(f"risk:drawdown:{p['symbol']}", drop, f"{p['symbol']} ירדה {drop:.0f}% מהשיא השנתי",
                    f"<p>{html.escape(p['name'])} נסחרת {drop:.1f}% מתחת לשיא של 52 השבועות האחרונים ({high:,.2f}).</p>")
        if p.get("return_ils_pct") is not None and p["return_ils_pct"] <= -config["drawdown_alert_pct"]:
            add(f"risk:loss:{p['symbol']}", p["return_ils_pct"], f"{p['symbol']}: {p['return_ils_pct']:.0f}% מאז הקנייה",
                f"<p>ההחזקה ב-{html.escape(p['name'])} נמצאת בהפסד מצטבר של {p['return_ils_pct']:.1f}% בשקלים מאז הקנייה.</p>")

    for sector, weight in exp["by_sector"].items():
        if sector != "לא ידוע" and not sector.startswith("ETF") and weight > config["sector_limit_pct"]:
            add(f"risk:sector:{sector}", weight, f"חשיפה ענפית: {sector} {weight:.0f}%",
                f"<p>{weight:.1f}% מהתיק בענף {html.escape(sector)} (הסף: {config['sector_limit_pct']:.0f}%).</p>")

    last_split = state.get("market_split")
    if last_split:
        for market, weight in exp["by_market"].items():
            shift = weight - last_split.get(market, 0)
            if abs(shift) >= config["market_shift_pct"]:
                add(f"risk:market:{market}", shift, f"שינוי בחשיפה ל{market}: {shift:+.0f} נק'",
                    f"<p>החשיפה לשוק {market} השתנתה מ-{last_split.get(market, 0):.0f}% ל-{weight:.0f}% מהתיק.</p>")

    fx = market_data._history("ILS=X", period="1mo", auto_adjust=False)["Close"]
    if len(fx) > 5:
        fx_change = (fx.iloc[-1] / fx.iloc[-6] - 1) * 100
        usd_weight = exp["by_currency"].get("USD", 0) or 0
        if abs(fx_change) >= config["fx_weekly_alert_pct"] and usd_weight:
            add("risk:fx:USD", fx_change, f"הדולר {'התחזק' if fx_change > 0 else 'נחלש'} {fx_change:+.1f}% מול השקל",
                f"<p>שער הדולר זז {fx_change:+.1f}% ב-5 ימי מסחר (כעת {fx.iloc[-1]:.3f} ₪). "
                f"{usd_weight:.0f}% מהתיק צמוד לדולר, ולכן שוויו בשקלים {'עלה' if fx_change > 0 else 'ירד'} "
                f"בכ-{abs(fx_change) * usd_weight / 100:.1f}% רק בגלל המטבע.</p>")
    return findings


def new_risk_alerts(findings: list[dict], state: dict) -> list[dict]:
    current = {f["key"] for f in findings}
    for key in [k for k in state["sent"] if k.startswith("risk:") and k not in current]:
        del state["sent"][key]  # resolved; alert again if it comes back
    return [f for f in findings if f["key"] not in state["sent"] or f["level"] > state["sent"][f["key"]]["level"]]


# ---------- email ----------

KIND_LABELS = {"price": "התרעת מחיר", "event": "אירוע מהותי", "risk": "סיכון בתיק", "data": "תקלה בנתונים"}


def render_alert_email(alerts: list[dict]) -> tuple[str, str]:
    if len(alerts) == 1:
        subject = f"{KIND_LABELS[alerts[0]['kind']]}: {alerts[0]['title']}"
    else:
        subject = f"{len(alerts)} התרעות בתיק: " + " | ".join(a["title"] for a in alerts[:3])
    cards = "".join(
        f"<div style='border:1px solid #ddd;border-radius:8px;padding:12px 16px;margin:12px 0'>"
        f"<div style='color:#666;font-size:13px'>{KIND_LABELS[a['kind']]}</div>"
        f"<h2 style='margin:4px 0 8px;font-size:18px'>{html.escape(a['title'])}</h2>{a['body']}</div>"
        for a in alerts
    )
    body = f"""<!doctype html><html dir="rtl" lang="he"><body style="font-family:Arial,sans-serif;line-height:1.6;
max-width:640px;margin:auto;color:#222">{cards}
<p style="color:#888;font-size:12px">נשלח על ידי אנליסט ההשקעות האישי שלך. המידע אינו ייעוץ השקעות; ההחלטות בידייך.
המערכת אינה מבצעת פעולות בחשבון.</p></body></html>"""
    return subject, body


# ---------- main entry ----------

def run_monitor(now: datetime | None = None, dry_run: bool = False, force: bool = False) -> dict:
    """One monitoring pass. Returns counts only, safe to print in public logs."""
    now = now or datetime.now(timezone.utc)
    config, state = load_config(), load_state()
    holdings = list(load_portfolio()["holdings"])
    if not holdings:
        return {"status": "no holdings"}

    collect_filings(state, now)
    open_symbols = {s for s in holdings if force or markets.is_open(s, now)}
    if not open_symbols:
        _save(STATE_FILE, state)
        return {"status": "markets closed", "pending_events": len(state["pending"])}

    try:
        valuation = value_portfolio(config["verify_tolerance_pct"])
    except Exception as e:
        valuation = None
        log_error("Valuation failed", e)
    live = [p for p in (valuation or {}).get("positions", []) if p.get("live")]
    alerts: list[dict] = []

    if not live:
        state["failures"] += 1
        if state["failures"] >= config["data_failure_runs"] and not state["failure_notified"]:
            alerts.append({"key": "data:failure", "level": 0, "kind": "data", "symbol": None,
                           "title": "לא התקבלו מחירים", "body": f"<p>ב-{state['failures']} הבדיקות האחרונות לא התקבלו "
                           "מחירים מספק הנתונים. ההתרעות לא פעילות עד שהבעיה תיפתר. פרטים ביומן השגיאות.</p>"})
            state["failure_notified"] = True
    else:
        state["failures"], state["failure_notified"] = 0, False
        alerts += price_alerts(valuation, config, state, open_symbols, now)
        today = now.date().isoformat()
        if state.get("last_risk_check") != today:
            state["last_risk_check"] = today
            try:
                findings = risk_findings(valuation, config, state)
                alerts += new_risk_alerts(findings, state)
            except Exception as e:
                log_error("Risk check failed", e)
            state.setdefault("market_split", exposures(valuation)["by_market"])

    alerts += due_events(state, open_symbols)
    result = {"status": "checked", "open_markets": sorted({markets.market_of(s) for s in open_symbols}),
              "holdings_priced": len(live), "alerts": len(alerts), "pending_events": len(state["pending"])}

    if alerts:
        subject, body = render_alert_email(alerts)
        delivery = send_email(subject, body, dry_run=dry_run)
        if delivery["sent"] or dry_run or not delivery["configured"]:
            status = "sent" if delivery["sent"] else "outbox"
            for a in alerts:
                state["sent"][a["key"]] = {"level": a["level"], "direction": a.get("direction"),
                                           "time": now.isoformat(timespec="minutes")}
                _log(state, now, a["kind"], a["symbol"], a["title"], status)
        else:  # SMTP failure: keep events queued and let the next run retry
            state["pending"] += [a for a in alerts if a["kind"] == "event"]
            for a in alerts:
                _log(state, now, a["kind"], a["symbol"], a["title"], "send-failed")
        result["email"] = "sent" if delivery["sent"] else "outbox"
    _save(STATE_FILE, state)
    return result
