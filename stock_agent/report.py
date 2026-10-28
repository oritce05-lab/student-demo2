"""Weekly portfolio report in Hebrew: numbers computed here, narrative written by Claude.

Sections follow the spec: A snapshot, B holdings, C news & events, D risk, E next week.
"""

from __future__ import annotations

import html
from datetime import datetime, timedelta, timezone

from . import ai, indicators, market_data
from .config import load_config
from .monitor import load_state, STATE_FILE
from .notify import log_error, send_email
from .portfolio import _home, _load, _save, load_portfolio
from .valuation import exposures, fx_on, value_portfolio

SNAPSHOTS_FILE = "snapshots.json"


def _close_on_or_before(symbol: str, day: datetime) -> float | None:
    closes = market_data._history(symbol, period="1mo", auto_adjust=False)["Close"]
    index = closes.index.tz_localize(None) if closes.index.tz else closes.index
    before = closes[index <= day.replace(tzinfo=None)]
    return float(before.iloc[-1]) if len(before) else None


def _weekly_change(symbol: str, now: datetime) -> float | None:
    try:
        then = _close_on_or_before(symbol, now - timedelta(days=7))
        latest = float(market_data._history(symbol, period="5d", auto_adjust=False)["Close"].iloc[-1])
        return (latest / then - 1) * 100 if then else None
    except Exception:
        return None


def _upcoming_earnings(symbol: str, now: datetime) -> str | None:
    try:
        calendar = market_data.yf.Ticker(symbol).calendar or {}
        dates = calendar.get("Earnings Date") or []
        upcoming = [d for d in dates if now.date() <= d <= (now + timedelta(days=14)).date()]
        return upcoming[0].isoformat() if upcoming else None
    except Exception:
        return None


def build_report_data(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    config = load_config()
    valuation = value_portfolio(config["verify_tolerance_pct"])
    week_ago = now - timedelta(days=7)
    usd_now = valuation["usd_ils"]
    usd_then = fx_on("USD", week_ago.date().isoformat())
    limitations = list(valuation["limitations"])

    holdings, prev_total, fx_effect_total = [], 0.0, 0.0
    for p in valuation["positions"]:
        row = {k: p.get(k) for k in ("symbol", "name", "market", "quantity", "currency", "price", "value_ils",
                                     "value_usd", "weight_pct", "return_native_pct", "return_ils_pct", "gain_ils",
                                     "sector", "is_etf", "live", "as_of")}
        if p.get("live"):
            try:
                price_then = _close_on_or_before(p["symbol"], week_ago)
                fx_then = fx_on(p["currency"], week_ago.date().isoformat())
                value_then = p["quantity"] * price_then * fx_then
                row["week_change_native_pct"] = (p["price"] / price_then - 1) * 100
                row["week_change_ils"] = p["value_ils"] - value_then
                row["week_change_ils_pct"] = (p["value_ils"] / value_then - 1) * 100
                row["week_fx_effect_ils"] = p["quantity"] * price_then * (p["fx_to_ils"] - fx_then)
                prev_total += value_then
                fx_effect_total += row["week_fx_effect_ils"]
            except Exception:
                limitations.append(f"{p['symbol']}: אין מחיר מלפני שבוע, לכן אין שינוי שבועי.")
            try:
                closes = market_data._history(p["symbol"], period="3mo")["Close"]
                row["volatility_3m_pct"] = indicators.annualized_volatility(closes) * 100
                row["max_drawdown_3m_pct"] = indicators.max_drawdown(closes) * 100
            except Exception:
                pass
            row["upcoming_earnings"] = _upcoming_earnings(p["symbol"], now)
        holdings.append(row)

    current_total = sum(h["value_ils"] for h in holdings if "week_change_ils" in h)
    snapshots = _load(SNAPSHOTS_FILE, {"weeks": []})["weeks"]
    previous = snapshots[-1] if snapshots else None
    week_events = [e for e in load_state()["log"]
                   if e["time"] >= week_ago.isoformat(timespec="minutes") and e["status"] in ("sent", "outbox")]
    return {
        "report_date": now.date().isoformat(),
        "investor": config["investor"],
        "price_source": "Yahoo Finance (מחירי סגירה; ייתכן עיכוב)",
        "usd_ils_now": usd_now,
        "usd_ils_week_ago": usd_then,
        "usd_ils_week_change_pct": (usd_now / usd_then - 1) * 100,
        "total_value_ils": valuation["total_value_ils"],
        "total_value_usd": valuation["total_value_usd"],
        "cash_ils": valuation["cash_ils"],
        # Price-driven change of what is held today (deposits and new buys do not count as gains).
        "holdings_week_change_ils": current_total - prev_total if prev_total else None,
        "holdings_week_change_pct": (current_total / prev_total - 1) * 100 if prev_total else None,
        "holdings_week_fx_effect_ils": fx_effect_total if prev_total else None,
        # Change in total value since the previous report, which also includes deposits and withdrawals.
        "previous_report": previous,
        "total_change_since_last_report_ils": valuation["total_value_ils"] - previous["total_ils"] if previous else None,
        "benchmarks_week_change_pct": {name: _weekly_change(sym, now) for name, sym in config["benchmarks"].items()},
        "holdings": holdings,
        "exposures": exposures(valuation),
        "events_this_week": week_events,
        "limitations": limitations,
    }


# ---------- rendering ----------

def _m(value, unit="₪"):
    return "—" if value is None else f"{value:,.0f} {unit}"


def _p(value):
    if value is None:
        return "—"
    color = "#0a7d32" if value > 0 else "#c62828" if value < 0 else "#444"
    return f"<span style='color:{color}'>{value:+.1f}%</span>"


def _signed_m(value):
    if value is None:
        return "—"
    color = "#0a7d32" if value > 0 else "#c62828" if value < 0 else "#444"
    return f"<span style='color:{color}'>{value:+,.0f} ₪</span>"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th style='text-align:right;padding:6px;border-bottom:2px solid #ccc'>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td style='padding:6px;border-bottom:1px solid #eee'>{c}</td>" for c in r)
                   + "</tr>" for r in rows)
    return f"<table style='border-collapse:collapse;width:100%;font-size:14px'><tr>{head}</tr>{body}</table>"


def render_report(data: dict, sections: dict | None) -> str:
    s = sections or {}
    missing_ai = "<p><em>הניתוח המילולי לא זמין השבוע (אין חיבור ל-Claude). הנתונים בטבלאות מלאים.</em></p>"
    bench = " | ".join(f"{name}: {_p(v)}" for name, v in data["benchmarks_week_change_pct"].items())
    prev = data["previous_report"]

    holdings_rows = [[
        f"<strong>{html.escape(str(h['name']))}</strong><br><span style='color:#777'>{h['symbol']}</span>",
        f"{h['quantity']:,g}",
        _m(h["value_ils"]) + (f"<br><span style='color:#777'>{_m(h['value_usd'], '$')}</span>"
                              if h.get("currency") not in ("ILS", "ILA") and h.get("value_usd") else ""),
        f"{h['weight_pct']:.1f}%",
        _p(h.get("week_change_native_pct")) + "<br>" + _signed_m(h.get("week_change_ils")),
        (_p(h.get("return_ils_pct")) + (f"<br><span style='color:#777'>במטבע המקור: {_p(h['return_native_pct'])}</span>"
                                        if h.get("return_native_pct") is not None
                                        and h.get("currency") not in ("ILS", "ILA") else ""))
        if h.get("return_ils_pct") is not None else "חסרים נתוני עלות",
    ] for h in data["holdings"]]

    exp = data["exposures"]
    exposure_rows = ([["שוק", k, f"{v:.0f}%"] for k, v in exp["by_market"].items()]
                     + [["מטבע", k, f"{v:.0f}%"] for k, v in exp["by_currency"].items()]
                     + [["ענף", html.escape(k), f"{v:.0f}%"] for k, v in exp["by_sector"].items()])
    risk_rows = [[h["symbol"], _p(h.get("volatility_3m_pct")).replace("+", ""), _p(h.get("max_drawdown_3m_pct"))]
                 for h in data["holdings"] if h.get("volatility_3m_pct") is not None]
    events = "".join(f"<li>{e['time'][:10]} — {html.escape(e['title'])}</li>" for e in data["events_this_week"])
    earnings = "".join(f"<li>{h['symbol']}: פרסום דוחות צפוי ב-{h['upcoming_earnings']} (לפי Yahoo Finance)</li>"
                       for h in data["holdings"] if h.get("upcoming_earnings"))
    limitations = "".join(f"<li>{html.escape(x)}</li>" for x in dict.fromkeys(data["limitations"]))

    return f"""<!doctype html><html dir="rtl" lang="he"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>דוח שבועי {data['report_date']}</title></head>
<body style="font-family:Arial,sans-serif;line-height:1.6;max-width:720px;margin:auto;padding:12px;color:#222">
<h1 style="font-size:22px">דוח שבועי לתיק ההשקעות — {data['report_date']}</h1>

<h2>א׳ — תמונת מצב</h2>
<ul>
<li><strong>שווי התיק:</strong> {_m(data['total_value_ils'])} ({_m(data['total_value_usd'], '$')})</li>
<li><strong>שינוי שבועי בשווי ההחזקות:</strong> {_signed_m(data['holdings_week_change_ils'])} ({_p(data['holdings_week_change_pct'])}),
מתוכו השפעת שער הדולר: {_signed_m(data['holdings_week_fx_effect_ils'])}</li>
<li><strong>שער הדולר:</strong> {data['usd_ils_now']:.3f} ₪ ({_p(data['usd_ils_week_change_pct'])} בשבוע)</li>
<li><strong>מדדי ייחוס השבוע:</strong> {bench}</li>
{f"<li><strong>שינוי מול הדוח הקודם ({prev['date']}):</strong> {_signed_m(data['total_change_since_last_report_ils'])} (כולל הפקדות ומשיכות)</li>" if prev else ""}
</ul>
{s.get('summary') or missing_ai}

<h2>ב׳ — ביצועי ההחזקות</h2>
{_table(["נייר", "כמות", "שווי", "משקל", "שינוי שבועי", "מאז הקנייה (₪)"], holdings_rows)}

<h2>ג׳ — חדשות ואירועים</h2>
{f"<h3>התרעות שנשלחו השבוע</h3><ul>{events}</ul>" if events else "<p>לא נשלחו התרעות השבוע.</p>"}
{s.get('news') or missing_ai}

<h2>ד׳ — ניתוח סיכונים</h2>
{_table(["סוג", "קבוצה", "משקל"], exposure_rows)}
{"<h3>תנודתיות וירידות (3 חודשים)</h3>" + _table(["נייר", "תנודתיות שנתית", "ירידה מקסימלית"], risk_rows) if risk_rows else ""}
{s.get('risk_commentary') or missing_ai}

<h2>ה׳ — מה כדאי לבדוק בשבוע הבא</h2>
{f"<ul>{earnings}</ul>" if earnings else ""}
{s.get('next_week') or missing_ai}

<h2 style="font-size:16px">מגבלות הנתונים</h2>
<ul style="color:#555;font-size:13px">{limitations or "<li>אין מגבלות מיוחדות השבוע.</li>"}
<li>מקור המחירים: {data['price_source']}. נתונים אינם בזמן אמת.</li>
<li>שינוי שבועי מחושב על הכמויות הנוכחיות, ללא השפעת הפקדות. דיבידנדים לא נכללים בשינוי המחיר.</li></ul>
<p style="color:#888;font-size:12px">הדוח הוא כלי עזר ואינו ייעוץ השקעות. ההחלטות בידייך. המערכת אינה מבצעת פעולות בחשבון.</p>
</body></html>"""


def run_weekly_report(now: datetime | None = None, dry_run: bool = False) -> dict:
    now = now or datetime.now(timezone.utc)
    if not load_portfolio()["holdings"]:
        return {"status": "no holdings"}
    data = build_report_data(now)
    sections = ai.report_sections(data) if load_config()["ai_explanations"] else None
    page = render_report(data, sections)

    reports = _home() / "reports"
    reports.mkdir(exist_ok=True)
    path = reports / f"weekly-{data['report_date']}.html"
    path.write_text(page, encoding="utf-8")
    delivery = send_email(f"דוח שבועי לתיק — {data['report_date']}", page, dry_run=dry_run)

    # Remember this week for next week's comparison and for the market-shift risk check.
    snapshots = _load(SNAPSHOTS_FILE, {"weeks": []})
    snapshots["weeks"] = (snapshots["weeks"] + [{
        "date": data["report_date"], "total_ils": data["total_value_ils"], "total_usd": data["total_value_usd"],
        "usd_ils": data["usd_ils_now"], "by_market": data["exposures"]["by_market"],
    }])[-104:]
    _save(SNAPSHOTS_FILE, snapshots)
    state = _load(STATE_FILE, {})
    state["market_split"] = data["exposures"]["by_market"]
    _save(STATE_FILE, state)
    if not sections and ai.available():
        log_error("Weekly report sent without AI sections")
    return {"status": "report created", "holdings": len(data["holdings"]), "ai_sections": bool(sections),
            "email": "sent" if delivery["sent"] else "outbox", "path": str(path)}
