"""Material-event filings for US companies from SEC EDGAR (official, free, no API key).

SEC asks every caller to send a User-Agent with a name and email (env SEC_USER_AGENT),
and to stay under 10 requests per second.
"""

from __future__ import annotations

import json
import time
from datetime import date, timedelta
from urllib.request import Request, urlopen

from .portfolio import _load, _save

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

# Forms that can move a stock. 8-K is the "current report" for material events.
MATERIAL_FORMS = {"8-K", "8-K/A", "10-Q", "10-K", "6-K", "20-F", "SC 13D", "SC 13D/A"}

FORM_DESCRIPTIONS = {
    "8-K": "דיווח מיידי על אירוע מהותי",
    "8-K/A": "תיקון לדיווח מיידי",
    "10-Q": "דוח כספי רבעוני",
    "10-K": "דוח שנתי",
    "6-K": "דיווח של חברה זרה (לרוב תוצאות או אירוע מהותי)",
    "20-F": "דוח שנתי של חברה זרה",
    "SC 13D": "בעל מניות רכש מעל 5% עם כוונה להשפיע",
    "SC 13D/A": "עדכון החזקה של בעל מניות מהותי",
}

# 8-K item numbers -> what happened.
ITEM_DESCRIPTIONS = {
    "1.01": "התקשרות בהסכם מהותי",
    "1.02": "סיום הסכם מהותי",
    "1.03": "פשיטת רגל או כינוס נכסים",
    "1.05": "אירוע סייבר מהותי",
    "2.01": "השלמת רכישה או מכירה של נכסים",
    "2.02": "פרסום תוצאות כספיות",
    "2.03": "התחייבות פיננסית מהותית (חוב)",
    "2.05": "עלויות יציאה או ארגון מחדש",
    "2.06": "ירידת ערך מהותית",
    "3.01": "אזהרת מחיקה מהמסחר / אי עמידה בכללי הבורסה",
    "3.02": "הנפקה לא רשומה של מניות",
    "4.01": "החלפת רואה חשבון מבקר",
    "4.02": "אין להסתמך על דוחות כספיים קודמים",
    "5.01": "שינוי שליטה בחברה",
    "5.02": "שינוי בהנהלה או בדירקטוריון",
    "5.03": "שינוי בתקנון או בשנת הכספים",
    "5.07": "תוצאות הצבעה באסיפת בעלי מניות",
    "7.01": "גילוי לפי Regulation FD (מצגת / הודעה)",
    "8.01": "אירוע אחר",
    "9.01": "דוחות כספיים ונספחים",
}

# Items that are routine attachments on their own; a filing with only these is not alert-worthy.
ROUTINE_ITEMS = {"9.01", "5.07", "3.02"}


def _get_json(url: str, user_agent: str) -> dict:
    request = Request(url, headers={"User-Agent": user_agent, "Accept-Encoding": "identity"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def cik_for(ticker: str, user_agent: str) -> int | None:
    """Look up a ticker's CIK. The SEC list is cached and refreshed weekly."""
    week = "%d-W%02d" % date.today().isocalendar()[:2]
    cache = _load("sec_tickers.json", {})
    if cache.get("fetched") != week:
        data = _get_json(TICKERS_URL, user_agent)
        cache = {"fetched": week,
                 "map": {row["ticker"].upper(): row["cik_str"] for row in data.values()}}
        _save("sec_tickers.json", cache)
    # Yahoo writes share classes with "-" (BRK-B); SEC uses the same.
    return cache["map"].get(ticker.upper())


def describe(filing: dict) -> str:
    text = FORM_DESCRIPTIONS.get(filing["form"], filing["form"])
    items = [ITEM_DESCRIPTIONS.get(i, f"סעיף {i}") for i in filing.get("items", [])]
    return f"{text}: {', '.join(items)}" if items else text


def is_material(filing: dict) -> bool:
    if filing["form"] not in MATERIAL_FORMS:
        return False
    if filing["form"].startswith("8-K") and filing.get("items"):
        return any(i not in ROUTINE_ITEMS for i in filing["items"])
    return True


def recent_filings(ticker: str, user_agent: str, days: int = 10) -> list[dict]:
    """Material filings in the last `days` days, newest first. Empty for tickers SEC doesn't know (e.g. ETFs)."""
    cik = cik_for(ticker, user_agent)
    if cik is None:
        return []
    time.sleep(0.15)  # stay well under SEC's rate limit
    recent = _get_json(SUBMISSIONS_URL.format(cik=cik), user_agent)["filings"]["recent"]
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    filings = []
    for i, form in enumerate(recent["form"]):
        filed = recent["filingDate"][i]
        if filed < cutoff:
            break  # the list is sorted newest first
        accession = recent["accessionNumber"][i]
        filing = {
            "form": form,
            "date": filed,
            "accession": accession,
            "items": [x.strip() for x in recent.get("items", [""] * len(recent["form"]))[i].split(",") if x.strip()],
            "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/"
                   f"{recent['primaryDocument'][i]}",
        }
        if is_material(filing):
            filing["description"] = describe(filing)
            filings.append(filing)
    return filings
