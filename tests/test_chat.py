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

    def __init__(
        self, variable: str, universe: str, stat: str = "prevalence",
        *, tool_name: str = "analyze_subpopulation", extra_args: dict | None = None,
    ):
        self._tool_name = tool_name
        self._args = {"variable": variable, "universe": universe, "stat": stat}
        if extra_args:
            self._args.update(extra_args)
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
            # First turn: call the configured tool with our fixed arguments.
            self.tool_calls.append(self._tool_name)
            yield {"messageStart": {"role": "assistant"}}
            yield {"contentBlockStart": {"start": {"toolUse": {
                "toolUseId": "t1", "name": self._tool_name}}}}
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


# --- The query-time groupby table tool ---------------------------------------------------

def test_agent_invokes_groupby_table_for_by_group_question(df):
    """Given a by-group question, the agent calls groupby_table (via a stub model) and
    surfaces the deterministic weighted table with a design-based CI per group."""
    model = _ToolThenTextModel(
        variable="DIBINS_A", universe="DIBEV_A == 1", stat="prevalence",
        tool_name="groupby_table", extra_args={"groupby": "SEX_A"},
    )
    agent = chat.build_chat_agent(model=model)
    out = str(agent("insulin use by sex among diagnosed adults")).strip()
    assert model.tool_calls == ["groupby_table"]  # the agent invoked the table tool
    assert "by SEX_A" in out
    assert out.count("95% CI") == 2          # one weighted cell per sex
    assert "WTFA_A" in out                   # stated survey-weighted basis


def test_groupby_table_refuses_unverified_variable():
    out = chat.groupby_table("SMOKEV_A", "SEX_A")
    assert out.startswith("REFUSED")
    assert "verified" in out.lower()


def test_groupby_table_returns_aggregate_table_text(df):
    out = chat.groupby_table("DIBINS_A", "SEX_A", "prevalence", "DIBEV_A == 1")
    assert isinstance(out, str)
    assert "by SEX_A" in out and "95% CI" in out
    assert "SEX_A=1" in out and "SEX_A=2" in out


def test_groupby_table_surfaces_group_cap_error(df):
    # Grouping on a near-continuous column is refused with a clear message, not a huge table.
    out = chat.groupby_table("DIBINS_A", "WEIGHTLBTC_A", "prevalence", "DIBEV_A == 1")
    assert out.startswith("REFUSED")
    assert "cap" in out


# --- OKF column-summary lookup (the agent's grounding for what a column means) -----------

def test_okf_column_summary_for_verified_columns():
    dibev = chat.okf_column_summary("DIBEV_A")
    assert "[DIBEV_A]" in dibev
    assert "Ever told you had diabetes" in dibev        # label from the registry
    assert "valid codes: 1, 2" in dibev                 # codes
    assert "universe (skip-pattern)" in dibev           # skip-pattern surfaced

    dibins = chat.okf_column_summary("DIBINS_A")
    assert "Currently takes insulin" in dibins
    assert "DIBEV_A == 1" in dibins                      # analytical universe in prose


def test_okf_column_summary_is_honest_for_ungrounded_columns():
    # SEX_A is used only as a grouping column — no verified concept, so no fabricated meaning.
    sex = chat.okf_column_summary("SEX_A")
    assert "no OKF summary" in sex
    assert "SEX_A" in sex

    # A column absent from the bundle entirely also gets the graceful note, never a guess.
    unknown = chat.okf_column_summary("NOPE_NOT_A_COLUMN")
    assert "no OKF summary" in unknown


# --- Retrieval-only runtime tool mode ----------------------------------------------------

def _tool_names(tools) -> set[str]:
    names = set()
    for t in tools:
        name = getattr(t, "tool_name", None) or getattr(t, "__name__", None)
        if name is None:
            spec = getattr(t, "tool_spec", None)
            if isinstance(spec, dict):
                name = spec.get("name")
        names.add(name)
    return names


def test_retrieval_mode_registers_only_search_tool(monkeypatch):
    monkeypatch.setenv("NHIS_RUNTIME_TOOLS", "retrieval")
    names = _tool_names(chat._as_tools())
    assert names == {"search_verified_okf"}


def test_default_mode_registers_full_local_tool_set(monkeypatch):
    monkeypatch.delenv("NHIS_RUNTIME_TOOLS", raising=False)
    names = _tool_names(chat._as_tools())
    assert names == {
        "search_verified_okf", "analyze_subpopulation", "groupby_table", "inspect_rows",
    }
    # The row-inspection tool is a DEFAULT-mode-only, local capability.
    assert "inspect_rows" in names


def test_retrieval_only_agent_has_single_tool(monkeypatch):
    """The built agent in retrieval mode carries only the verified-bundle retrieval tool."""
    monkeypatch.setenv("NHIS_RUNTIME_TOOLS", "retrieval")
    from strands.models import Model

    class _Idle(Model):
        def update_config(self, **_k): pass
        def get_config(self): return {}
        async def structured_output(self, *_a, **_k): yield {}
        async def stream(self, *_a, **_k):
            yield {"messageStart": {"role": "assistant"}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}

    agent = chat.build_chat_agent(model=_Idle())
    names = set(agent.tool_registry.get_all_tools_config().keys())
    assert names == {"search_verified_okf"}


def test_building_retrieval_tools_does_not_import_analysis():
    """Building the retrieval-only tool set must not import our pandas-bearing `analysis`
    module — the property that keeps the packaged CodeZip pandas-free (the runtime installs
    no pandas). Run in a fresh subprocess so the assertion is not contaminated by imports
    other tests performed in this process.

    Note: we assert on `nhis_okf.analysis`, not `pandas` in sys.modules — the local venv has
    sklearn, which *optionally* imports pandas if present. In the deploy container pandas is
    not installed and sklearn works without it; the meaningful guard is that our compute path
    (which requires pandas) is never loaded.
    """
    import subprocess
    import sys

    code = (
        "import os, sys\n"
        "os.environ['NHIS_RUNTIME_TOOLS'] = 'retrieval'\n"
        "from nhis_okf import chat\n"
        "tools = chat._as_tools()\n"
        "assert 'nhis_okf.analysis' not in sys.modules, 'analysis was imported'\n"
        "assert 'nhis_okf.compiler' not in sys.modules, 'compiler (pandas) was imported'\n"
        "assert 'nhis_okf.parquet_query' not in sys.modules, 'parquet_query (row tool) imported'\n"
        "print('OK', len(tools))\n"
    )
    res = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == "OK 1"
