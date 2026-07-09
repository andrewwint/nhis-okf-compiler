"""The subpopulation query returns a survey-weighted aggregate + design CI and NEVER a
row set, and the CLI is grounded-or-refuse."""

import inspect

import pandas as pd
import pytest

from nhis_okf import analysis, cli


def test_mean_subpopulation_returns_aggregate_with_ci(df):
    res = analysis.subpopulation_stat(
        df, "DIBAGETC_A", universe_expr="DIBEV_A == 1", stat="mean"
    )
    assert res.unit == ""  # years, not a percentage
    assert abs(res.estimate - 47.41) < 0.5
    assert res.lci < res.estimate < res.uci
    assert res.se > 0
    # The result is a scalar aggregate object, not a DataFrame of rows.
    assert not isinstance(res, pd.DataFrame)
    assert not hasattr(res, "iterrows")


def test_prevalence_subpopulation_has_design_ci(df):
    res = analysis.subpopulation_stat(
        df, "DIBINS_A", universe_expr="DIBEV_A == 1", stat="prevalence"
    )
    assert res.unit == "%"
    assert res.lci < res.estimate < res.uci


def test_quantile_subpopulation_returns_ci(df):
    res = analysis.subpopulation_stat(
        df, "DIBAGETC_A", universe_expr="DIBEV_A == 1", stat="quantile", q=0.5
    )
    assert res.q == 0.5
    assert res.lci <= res.estimate <= res.uci


def test_summary_emits_no_individual_rows(df):
    res = analysis.subpopulation_stat(
        df, "DIBAGETC_A", universe_expr="DIBEV_A == 1", stat="mean"
    )
    text = res.summary()
    # Aggregate framing only: an estimate, a CI, a weighted denominator — no per-row data.
    assert "CI" in text and "weighted" in text


def test_unverified_variable_is_refused(monkeypatch, capsys):
    # Pretend only DIBEV_A is verified in the bundle.
    monkeypatch.setattr(cli, "_verified_variables", lambda: {"DIBEV_A"})
    args = type("A", (), {"variable": "DIBAGETC_A", "universe": None, "stat": "mean", "q": 0.5})()
    rc = cli.cmd_analyze(args)
    assert rc == 2
    assert "refused" in capsys.readouterr().err.lower()


def test_empty_universe_refuses_not_fabricates_zero(df):
    # An arbitrary universe matching no substantive rows must raise, never report a
    # confidently-wrong 0.0 with a NaN interval.
    with pytest.raises(ValueError, match="empty subpopulation"):
        analysis.subpopulation_stat(
            df, "DIBAGETC_A", universe_expr="DIBEV_A == 999", stat="mean"
        )


def test_trust_boundary_note_is_preserved():
    src = inspect.getsource(analysis._mask)
    assert "trust boundary" in src.lower()
    assert "eval" in src.lower()
