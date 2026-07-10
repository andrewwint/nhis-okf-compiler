"""The researcher row tool (`nhis rows` / parquet_query) is the ONE surface that returns
raw individual rows — a few columns, capped, loudly labeled — and it stays structurally
out of the verified product and the deployed grounded agent."""

import inspect
from pathlib import Path

import pandas as pd
import pytest

from nhis_okf import analysis, chat, cli, parquet_query

# agentcore_app imports a deploy-only dependency (bedrock_agentcore), so read its source
# from disk rather than importing it.
_AGENT_SRC = Path(chat.__file__).with_name("agentcore_app.py").read_text()


# --- The row tool returns the requested columns for a subpopulation ----------------------

def test_returns_requested_columns_for_subpopulation(df):
    rows = parquet_query.query_rows(
        ["DIBEV_A", "DIBINS_A", "SEX_A"], universe_expr="DIBEV_A == 1", limit=5
    )
    assert isinstance(rows, pd.DataFrame)
    assert list(rows.columns) == ["DIBEV_A", "DIBINS_A", "SEX_A"]  # exactly, in order
    assert len(rows) == 5
    assert (rows["DIBEV_A"] == 1).all()  # the universe filter was applied


def test_universe_columns_need_not_be_requested(df):
    # The filter references a column that is not in the projection — still works.
    rows = parquet_query.query_rows(["SEX_A"], universe_expr="DIBEV_A == 1", limit=3)
    assert list(rows.columns) == ["SEX_A"]
    assert len(rows) == 3


# --- Caveat header is present on every CLI call ------------------------------------------

def test_cli_prints_loud_caveat_before_rows(df, capsys):
    args = type("A", (), {"columns": "DIBEV_A,DIBINS_A", "universe": "DIBEV_A == 1",
                          "limit": 5})()
    rc = cli.cmd_rows(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "RAW MICRODATA ROWS" in out
    assert "UNWEIGHTED" in out
    assert "not verified" in out.lower()
    assert "nhis analyze" in out
    # The caveat precedes the data.
    assert out.index("RAW MICRODATA ROWS") < out.index("DIBEV_A")


# --- Row cap: default limit and hard max -------------------------------------------------

def test_limit_caps_rows(df):
    rows = parquet_query.query_rows(["SEX_A"], universe_expr="DIBEV_A == 1", limit=7)
    assert len(rows) == 7


def test_hard_max_limit_enforced(df):
    over = parquet_query.HARD_MAX_LIMIT + 1000
    rows = parquet_query.query_rows(["SEX_A"], limit=over)
    assert len(rows) <= parquet_query.HARD_MAX_LIMIT


def test_bad_limit_errors():
    with pytest.raises(ValueError, match="limit must be"):
        parquet_query.query_rows(["SEX_A"], limit=0)


# --- Explicit, bounded column list -------------------------------------------------------

def test_empty_columns_errors():
    with pytest.raises(ValueError, match="explicit non-empty column list"):
        parquet_query.query_rows([])


def test_cli_missing_columns_refuses(capsys):
    args = type("A", (), {"columns": "", "universe": None, "limit": 20})()
    rc = cli.cmd_rows(args)
    assert rc == 2
    assert "columns" in capsys.readouterr().err.lower()


def test_too_many_columns_errors():
    cols = [f"C{i}" for i in range(parquet_query.MAX_COLUMNS + 1)]
    with pytest.raises(ValueError, match="too many columns"):
        parquet_query.query_rows(cols)


def test_unknown_column_errors(df):
    with pytest.raises(ValueError, match="unknown column"):
        parquet_query.query_rows(["NOPE_NOT_A_COLUMN"])


# --- Boundary: the verified product and deployed agent cannot reach the row tool ----------

def test_analyze_path_stays_aggregate_only(df):
    # subpopulation_stat returns a scalar aggregate, never a row set.
    res = analysis.subpopulation_stat(df, "DIBINS_A", universe_expr="DIBEV_A == 1")
    assert not isinstance(res, pd.DataFrame)
    assert not hasattr(res, "iterrows")


def test_agent_modules_do_not_import_row_tool():
    """The deployed grounded agent must be structurally unable to emit rows: neither
    chat.py nor agentcore_app.py may import the row-query tool."""
    assert "parquet_query" not in inspect.getsource(chat), "chat.py must not reference parquet_query"
    assert not hasattr(chat, "parquet_query")
    assert "parquet_query" not in _AGENT_SRC, "agentcore_app.py must not reference parquet_query"


def test_trust_boundary_note_reused_by_row_tool():
    # The row tool filters via analysis._mask, whose df.eval trust-boundary note stands.
    src = inspect.getsource(parquet_query.query_rows)
    assert "_mask" in src
    assert "trust" in src.lower()


# --- OKF usage instructions: Reference concept + per-concept Reproduce blocks -------------

def test_reference_concept_emitted_and_conformant(df, tmp_path):
    from nhis_okf.compiler import compile_bundle, check_conformance, _split_frontmatter

    out = tmp_path / "variables"
    compile_bundle(df, out_dir=out, log_path=tmp_path / "log.md")
    ref = tmp_path / "references" / "parquet_query.md"
    assert ref.exists()
    fm = _split_frontmatter(ref.read_text())
    assert fm is not None and fm.get("type") == "Reference"
    ok, issues = check_conformance(tmp_path)
    assert ok, f"conformance failed with reference present: {issues}"


def test_analytical_concepts_carry_reproduce_block(df, tmp_path):
    from nhis_okf.compiler import compile_bundle

    out = tmp_path / "variables"
    compile_bundle(df, out_dir=out, log_path=tmp_path / "log.md")
    dibins = (out / "DIBINS_A.md").read_text()
    assert "## Reproduce" in dibins
    assert 'nhis analyze --variable DIBINS_A --universe "DIBEV_A == 1"' in dibins
    assert "nhis rows --columns" in dibins
    assert 'DIBINS_A' in dibins
