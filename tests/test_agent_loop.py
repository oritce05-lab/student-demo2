from types import SimpleNamespace as NS

from stock_agent import agent as agent_module
from stock_agent.agent import StockAgent


class FakeMessages:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.responses.pop(0)


def test_tool_loop_runs_tool_and_returns_final_text(monkeypatch):
    monkeypatch.setitem(agent_module.TOOLS, "get_quote", lambda symbol: {"symbol": symbol, "price": 123.0})
    fake = FakeMessages([
        NS(stop_reason="tool_use", content=[NS(type="tool_use", id="t1", name="get_quote", input={"symbol": "AAPL"})]),
        NS(stop_reason="end_turn", content=[NS(type="text", text="AAPL is at 123.")]),
    ])
    agent = StockAgent(client=NS(beta=NS(messages=fake)), verbose=False)

    assert agent.ask("מה המחיר של אפל?") == "AAPL is at 123."
    tool_result = fake.calls[1]["messages"][-1]["content"][0]
    assert tool_result["tool_use_id"] == "t1" and not tool_result["is_error"]
    assert '"price": 123.0' in tool_result["content"]
    assert fake.calls[0]["fallbacks"] == "default"
