"""Claude-written text for alerts and the weekly report.

The numbers are always computed in Python; Claude only explains them and searches for news.
If the API is unavailable, callers fall back to data-only messages.
"""

from __future__ import annotations

import json
import os

import anthropic

from .config import MODEL
from .notify import log_error

WRITING_RULES = """Rules:
- Write in simple Hebrew for a beginner investor (horizon 5+ years, medium risk).
- Use only the numbers given to you and facts you found with web search. Never invent or estimate missing data; \
say plainly when information is missing or unclear.
- Separate facts (with source link and publication date) from assessments and forecasts, and label each.
- Show risks and alternatives, not only the positive scenario. Do not recommend selling just because a price fell, \
and do not tell the reader to buy or sell - point out what is worth checking before deciding.
- Output HTML fragments only (p, ul, li, a, strong, h3). No <html>/<body>, no markdown, no code fences."""


def available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _run(prompt: str, max_searches: int, effort: str, max_tokens: int) -> str | None:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": prompt}]
    for _ in range(5):  # pause_turn continuations for long searches
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            output_config={"effort": effort},
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": max_searches}],
            messages=messages,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            response = stream.get_final_message()
        if response.stop_reason == "refusal":
            return None
        if response.stop_reason != "pause_turn":
            text = "".join(b.text for b in response.content if b.type == "text").strip()
            return text.removeprefix("```html").removesuffix("```").strip() or None
        messages.append({"role": "assistant", "content": response.content})
    return None


def explain_move(position: dict) -> str | None:
    """Short, sourced explanation for a large daily move, or None."""
    if not available():
        return None
    facts = {k: position.get(k) for k in ("symbol", "name", "market", "price", "previous_close", "change_pct",
                                          "currency", "as_of")}
    prompt = (
        "A stock in the investor's portfolio moved sharply today. Search for a reliable reason "
        "(company filing, earnings, guidance, news from a reputable outlet; for Israeli companies check MAYA "
        "maya.tase.co.il reports and Israeli financial press). Answer in 2-4 sentences with source links. "
        "If you find no reliable reason, say so - do not speculate.\n\n"
        f"{WRITING_RULES}\n\nData:\n{json.dumps(facts, ensure_ascii=False, default=str)}"
    )
    try:
        return _run(prompt, max_searches=3, effort="low", max_tokens=8000)
    except anthropic.APIError as e:
        log_error(f"AI explanation failed for {position.get('symbol')}", e)
        return None


REPORT_SECTIONS = ["summary", "news", "risk_commentary", "next_week"]


def report_sections(report_data: dict) -> dict | None:
    """Narrative parts of the weekly report, keyed by REPORT_SECTIONS, or None."""
    if not available():
        return None
    prompt = f"""You are writing the narrative parts of a weekly portfolio report. The tables are rendered \
separately from the data below; do not repeat them, interpret them.

Write four HTML fragments, each preceded by a marker line exactly like <!--SECTION:name-->:
<!--SECTION:summary--> 3-5 sentences: what happened to the portfolio this week and why, vs. the benchmarks, \
including the USD/ILS effect.
<!--SECTION:news--> The most important news and filings this week for the holdings (use web search; for \
US companies prefer SEC filings and company releases, for Israeli companies MAYA reports and reputable Israeli \
financial press). For each item: what happened, what it means in plain words, fact vs. assessment, source link \
and date. Skip holdings with nothing material; say so briefly.
<!--SECTION:risk_commentary--> Explain the concentration, sector, market and currency exposures and the notable \
drawdowns in the data, and what deserves monitoring.
<!--SECTION:next_week--> Upcoming earnings dates and expected events for the holdings next week (verify dates \
with search), unusual changes that need attention, and 2-4 questions worth asking before any investment decision.

{WRITING_RULES}

Data (JSON):
{json.dumps(report_data, ensure_ascii=False, default=str)}"""
    try:
        text = _run(prompt, max_searches=10, effort="medium", max_tokens=32000)
    except anthropic.APIError as e:
        log_error("AI weekly report sections failed", e)
        return None
    if not text:
        return None
    sections = {}
    for part in text.split("<!--SECTION:")[1:]:
        name, _, body = part.partition("-->")
        if name.strip() in REPORT_SECTIONS:
            sections[name.strip()] = body.strip()
    return sections or None
