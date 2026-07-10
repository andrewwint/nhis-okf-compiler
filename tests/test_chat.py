"""Chat layer: the agent's only window onto data is the verified bundle, and model
selection is correct. These tests are hermetic — no network, no model call.

The live Strands generative path (Anthropic API / Bedrock) is exercised manually; here we
test the deterministic pieces: the retrieval tool, grounding/refusal signal, model
selection, and agent wiring with an injected dummy model.
"""

import json

from strands.models import Model

from nhis_okf import chat, config


class _ToolThenTextModel(Model):
    """A hermetic stub Strands model: on its first turn it emits a tool-use for
    analyze_subpopulation, then on the follow-up turn (after the tool result is fed back)
    it emits a short final answer that quotes the tool's aggregate. No network, no API.
    """

    def __init__(self, variable: str, universe: str, stat: str = "prevalence"):
        self._args = {"variable": variable, "universe": universe, "stat": stat}
        self.tool_calls: list[str] = []

    def update_config(self, **_kwargs):  # pragma: no cover - interface stub
        pass

    def get_config(self):  # pragma: no cover - interface stub
        return {}

    async def structured_output(self, *_a, **_k):  # pragma: no cover - unused
        yield {}

    @staticmethod
    def _tool_result_text(messages) -> str | None:
        for msg in messages:
            for block in msg.get("content", []) if isinstance(msg, dict) else []:
                tr = block.get("toolResult") if isinstance(block, dict) else None
                if tr:
                    for c in tr.get("content", []):
                        if "text" in c:
                            return c["text"]
        return None

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        tool_text = self._tool_result_text(messages)
        if tool_text is None:
            # First turn: call analyze_subpopulation with our fixed arguments.
            self.tool_calls.append("analyze_subpopulation")
            yield {"messageStart": {"role": "assistant"}}
            yield {"contentBlockStart": {"start": {"toolUse": {
                "toolUseId": "t1", "name": "analyze_subpopulation"}}}}
            yield {"contentBlockDelta": {"delta": {"toolUse": {
                "input": json.dumps(self._args)}}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            # Second turn: quote the deterministic aggregate the tool returned.
            yield {"messageStart": {"role": "assistant"}}
            yield {"contentBlockDelta": {"delta": {"text": tool_text}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}


def test_tool_returns_verified_figure_for_in_bundle_query():
    out = chat.search_verified_okf("how many adults with diabetes take insulin?")
    assert "DIBINS_A" in out
    assert "31.96" in out
    assert "3.66" not in out  # the quarantined number is never reachable


def test_tool_only_ever_surfaces_verified_concepts():
    """For an out-of-bundle query the tool may return weak verified matches, but it can
    never fabricate a figure or surface the quarantined number. Refusal-on-irrelevance is
    the agent's job (verified live against the real API), not the tool's."""
    out = chat.search_verified_okf("prevalence of asthma among adults")
    assert "3.66" not in out          # quarantined number is unreachable
    assert "asthma" not in out.lower()  # the tool cannot invent an asthma figure


def test_format_hits_empty_is_refusal_signal():
    assert chat._format_hits([]) == "NO_VERIFIED_CONCEPTS_FOUND"


def test_model_selection_prefers_anthropic_when_key_present(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")
    assert config.has_anthropic_key() is True


def test_model_selection_falls_back_to_bedrock_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert config.has_anthropic_key() is False


def test_build_agent_uses_anthropic_when_key_present(monkeypatch):
    """With a key set, the agent builds on the Anthropic provider. Construction is offline
    (the client only calls the API at invoke time), so this needs no network."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")
    from strands.models.anthropic import AnthropicModel

    agent = chat.build_chat_agent()
    assert agent is not None
    assert isinstance(getattr(agent, "model", None), AnthropicModel)


def test_over_long_question_is_rejected_before_any_model_call(monkeypatch):
    """Cost guardrail for the public no-auth endpoint: reject over-long input up front."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")  # would go generative
    ans = chat.answer("why " * 400)  # well over MAX_QUESTION_CHARS
    assert ans.mode == "rejected"
    assert "too long" in ans.text.lower()


def test_extractive_path_is_grounded(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ans = chat.answer("insulin among adults with diabetes", generative=False)
    assert ans.mode == "extractive"
    assert "31.96" in ans.text
    assert "not medical advice" in ans.text


# --- The query-time subpopulation tool ---------------------------------------------------

def test_agent_invokes_analyze_subpopulation_and_surfaces_figure_with_ci(df):
    """Given a subgroup question, the agent calls analyze_subpopulation (via a stub model)
    and surfaces the deterministic weighted figure with its design-based CI."""
    model = _ToolThenTextModel(
        variable="DIBINS_A", universe="DIBEV_A == 1 & SEX_A == 2", stat="prevalence"
    )
    agent = chat.build_chat_agent(model=model)
    out = str(agent("insulin use among diabetic women")).strip()
    assert model.tool_calls == ["analyze_subpopulation"]  # the agent invoked the tool
    assert "DIBINS_A" in out
    assert "%" in out and "CI" in out            # weighted estimate + design-based CI
    assert "weighted by" in out and "universe" in out  # stated basis


def test_analyze_subpopulation_refuses_unverified_variable():
    out = chat.analyze_subpopulation("SMOKEV_A", "AGEP_A > 40")
    assert out.startswith("REFUSED")
    assert "verified" in out.lower()


def test_analyze_subpopulation_returns_aggregate_text_not_rows(df):
    out = chat.analyze_subpopulation("DIBINS_A", "DIBEV_A == 1", "prevalence")
    assert isinstance(out, str)                  # scalar aggregate text, never a row set
    assert "CI" in out and "weighted by" in out
    assert "\n" not in out.strip()               # one aggregate line, no row dump


def test_analyze_subpopulation_refuses_empty_subpopulation(df):
    out = chat.analyze_subpopulation("DIBINS_A", "DIBEV_A == 999")
    assert out.startswith("REFUSED")
    assert "empty subpopulation" in out
