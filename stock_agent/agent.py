"""Interactive stock research agent: Claude + market-data tools + web search.

Run with:  python -m stock_agent
"""

from __future__ import annotations

import json
import sys
from datetime import date

import anthropic

from .market_data import TOOL_DEFINITIONS, TOOLS, ToolError

MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """You are a stock research assistant. You help users understand stocks, indices and \
markets using live data from your tools.

How to work:
- Always fetch fresh data with your tools before stating prices, returns or ratios. Never quote numbers from memory.
- Use get_quote / get_technical_indicators / get_company_info / compare_stocks / get_price_history for market data, \
and get_news or web_search for recent events and context. Call independent tools in parallel.
- Tel Aviv Stock Exchange tickers end with ".TA" (e.g. TEVA.TA, LUMI.TA, POLI.TA, ESLT.TA); TASE prices are in agorot (ILA). \
If the user names a company, figure out its ticker; if it is ambiguous, say which one you picked.
- Say where each figure came from (Yahoo Finance data vs. a web source) and the date it refers to.
- Explain indicators in plain language for non-experts, and present both bullish and bearish points.
- Reply in the user's language (Hebrew if they write in Hebrew).

You provide information and analysis, not personalized investment advice. When the user asks whether to buy or sell, \
give a balanced analysis and remind them briefly that this is not investment advice and they should consider their own \
situation or consult a licensed advisor."""

WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}


def run_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """Execute a client tool. Returns (content, is_error)."""
    func = TOOLS.get(name)
    if func is None:
        return f"Unknown tool: {name}", True
    try:
        return json.dumps(func(**tool_input), ensure_ascii=False, default=str), False
    except ToolError as e:
        return str(e), True
    except TypeError as e:  # wrong/missing arguments from the model
        return f"Invalid arguments for {name}: {e}", True
    except Exception as e:  # network or data-provider failure
        return f"{name} failed: {type(e).__name__}: {e}", True


class StockAgent:
    def __init__(self, client: anthropic.Anthropic | None = None, verbose: bool = True):
        self.client = client or anthropic.Anthropic()
        self.messages: list = []
        self.verbose = verbose

    def _log(self, text: str) -> None:
        if self.verbose:
            print(f"  \033[2m{text}\033[0m", file=sys.stderr)

    def ask(self, question: str) -> str:
        """Send one user message, run the tool loop to completion, and return the final text."""
        self.messages.append({"role": "user", "content": question})
        while True:
            response = self.client.beta.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=f"{SYSTEM_PROMPT}\n\nToday's date: {date.today().isoformat()}",
                thinking={"type": "adaptive"},
                output_config={"effort": "medium"},
                tools=[*TOOL_DEFINITIONS, WEB_SEARCH_TOOL],
                messages=self.messages,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "refusal":
                return "The model declined this request. Try rephrasing the question."
            if response.stop_reason == "pause_turn":  # long web search; send back to continue
                continue

            for block in response.content:
                if block.type == "server_tool_use":
                    self._log(f"web_search: {block.input.get('query', '')}")

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if response.stop_reason != "tool_use" or not tool_uses:
                text = "".join(b.text for b in response.content if b.type == "text")
                if response.stop_reason == "max_tokens":
                    text += "\n\n[Answer was cut off - ask me to continue.]"
                return text

            results = []
            for tool in tool_uses:
                self._log(f"{tool.name}({json.dumps(tool.input, ensure_ascii=False)})")
                content, is_error = run_tool(tool.name, tool.input)
                results.append({"type": "tool_result", "tool_use_id": tool.id, "content": content, "is_error": is_error})
            self.messages.append({"role": "user", "content": results})


def main() -> None:
    agent = StockAgent()
    print("סוכן מניות | Stock Agent  (exit / יציאה to quit)\n")
    if len(sys.argv) > 1:
        print(agent.ask(" ".join(sys.argv[1:])))
        return
    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in {"exit", "quit", "יציאה"}:
            break
        if not question:
            continue
        try:
            print(f"\n{agent.ask(question)}\n")
        except anthropic.AuthenticationError:
            print("Missing or invalid API key. Set ANTHROPIC_API_KEY.")
            break
        except anthropic.RateLimitError:
            print("Rate limited - wait a moment and try again.")
        except anthropic.APIConnectionError:
            print("Could not reach the Anthropic API - check your connection.")
        except anthropic.APIStatusError as e:
            print(f"API error {e.status_code}: {e.message}")
