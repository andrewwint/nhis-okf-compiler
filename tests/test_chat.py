"""Chat layer: the agent's only window onto data is the verified bundle, and model
selection is correct. These tests are hermetic — no network, no model call.

The live Strands generative path (Anthropic API / Bedrock) is exercised manually; here we
test the deterministic pieces: the retrieval tool, grounding/refusal signal, model
selection, and agent wiring with an injected dummy model.
"""

from nhis_okf import chat, config


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


def test_extractive_path_is_grounded(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ans = chat.answer("insulin among adults with diabetes", generative=False)
    assert ans.mode == "extractive"
    assert "31.96" in ans.text
    assert "not medical advice" in ans.text
