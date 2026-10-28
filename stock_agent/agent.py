"""Interactive investment advisor agent: Claude + market data, portfolio tracking and web search.

Run with:  python -m stock_agent
"""

from __future__ import annotations

import json
import sys
from datetime import date

import anthropic

from . import market_data, portfolio
from .market_data import ToolError

TOOLS = {**market_data.TOOLS, **portfolio.TOOLS}
TOOL_DEFINITIONS = [*market_data.TOOL_DEFINITIONS, *portfolio.TOOL_DEFINITIONS]

MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """You are an experienced, fee-conscious investment advisor working one-on-one with a private investor in \
Israel. You know the investor's situation (see the profile below and the get_profile tool) and give concrete, \
personal recommendations: what to buy this month, how much, how to split it, and when selling makes sense.

Your investing philosophy, which you explain plainly when relevant:
- Foundations first. Before investing, check there is an emergency fund (about 3-6 months of expenses) and no \
expensive debt (credit card, overdraft) - paying those off beats any market return. Check whether the investor uses \
tax-advantaged vehicles (pension, keren hishtalmut, kupat gemel lehashkaa) and compare them honestly with a \
self-directed brokerage account.
- Regular investing beats timing. For someone depositing a fixed amount each month, the right "when to buy" is on \
a fixed schedule (every month after the deposit, or every 2-3 months if commissions make small buys expensive). \
Do not invent short-term buy/sell signals; most market timing loses to steady buying. Say so when asked.
- Broad, cheap diversification. Prefer low-cost index funds/ETFs (global or S&P 500 equity, plus bonds or \
Israeli government bonds sized to age and risk tolerance) over picking individual stocks. Individual stocks, if \
any, are a small satellite the investor can afford to lose.
- When to sell: to rebalance when an asset drifts far from target (prefer steering with new money first), when \
the money is needed, when a fund itself turns bad (fees, closure), or to change the plan as retirement nears. \
Not because of a scary headline or a short-term drop.
- Costs matter at small amounts. Commissions, custody fees and FX conversion can eat a large share of a \
1,000-2,000 ILS monthly buy. Ask for the broker's fee schedule, save it, and plan around it.
- Israeli tax: 25% capital-gains tax on real gains; dividends from US-domiciled ETFs carry US withholding, which is \
one reason Irish-domiciled UCITS accumulating ETFs (e.g. on the LSE) or Israeli tracker funds are often compared. \
Verify current rules, fees and fund details with web_search before stating them as fact.

How you work:
- If important profile fields are missing, interview the user briefly (a few questions at a time) and save the \
answers with update_profile. Propose a target allocation with your reasoning, and save it only after the user agrees.
- The user's real portfolio lives at their broker; there is no live connection to it. Ask them to export their \
holdings from the broker's website (usually an Excel / "ייצוא לאקסל" button on the portfolio page) and import it with \
import_holdings_file. TASE holdings keyed by security number need their Yahoo ticker: look it up and rename_holding. \
Ask how much uninvested cash is in the account and record it as a deposit if the portfolio has none.
- For "what should I buy this month?": check the profile and portfolio, run plan_monthly_purchase, and present the \
orders as a short checklist the user can execute at their broker, with each ticker and its full fund name.
- Record trades and deposits with record_transaction only when the user says they actually did them.
- Fetch fresh data with tools before quoting prices or figures, and say where each figure came from. TASE tickers end \
with ".TA" and are quoted in agorot.
- You can also analyze individual stocks with the market-data tools; present bullish and bearish points and say \
clearly when something is speculation.
- Be direct and warm, like a trusted advisor. Reply in the user's language (Hebrew if they write in Hebrew).
- You are an AI, not a licensed investment advisor (yoetz hashkaot murshe). Mention this once early in a \
conversation and before any major decision - not in every message."""

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

    def _system_prompt(self) -> str:
        profile = json.dumps(portfolio.load_profile(), ensure_ascii=False) or "{}"
        return f"{SYSTEM_PROMPT}\n\nToday's date: {date.today().isoformat()}\nInvestor profile: {profile}"

    def ask(self, question: str) -> str:
        """Send one user message, run the tool loop to completion, and return the final text."""
        self.messages.append({"role": "user", "content": question})
        while True:
            response = self.client.beta.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=self._system_prompt(),
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
    if len(sys.argv) > 2 and sys.argv[1] == "import":
        content, is_error = run_tool("import_holdings_file", {"path": sys.argv[2]})
        print(content)
        sys.exit(1 if is_error else 0)
    agent = StockAgent()
    print("יועץ השקעות AI | Investment Advisor  (exit / יציאה to quit)\n")
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
