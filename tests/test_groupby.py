"""The deterministic weighted groupby table: one weighted aggregate cell per substantive
group value (each with a design-based CI), non-substantive group codes dropped, the group
count capped, and every cell equal to a direct per-group `subpopulation_stat` (no drift)."""

import pandas as pd
import pytest

from nhis_okf import analysis, cli


def test_groupby_prevalence_one_weighted_cell_per_group_with_ci(df):
    table = analysis.groupby_table(
        df, "DIBINS_A", "SEX_A", stat="prevalence", extra_universe="DIBEV_A == 1"
    )
    # SEX_A is 1/2 (7/9 dropped): exactly two weighted cells.
    assert [c.group_value for c in table.cells] == [1, 2]
    for cell in table.cells:
        r = cell.result
        assert r.unit == "%"
        assert r.lci < r.estimate < r.uci  # a real design-based CI
        assert r.unweighted_n > 0
    # Aggregate-only: cells are SubpopulationResults, never row sets.
    assert not any(isinstance(c.result, pd.DataFrame) for c in table.cells)


def test_groupby_mean_produces_weighted_cell_per_group(df):
    table = analysis.groupby_table(df, "WEIGHTLBTC_A", "SEX_A", stat="mean")
    assert [c.group_value for c in table.cells] == [1, 2]
    for cell in table.cells:
        r = cell.result
        assert r.unit == ""  # pounds, not a percentage
        assert r.lci < r.estimate < r.uci


def test_non_substantive_group_codes_are_dropped(df):
    # SEX_A carries 7/9 reserved codes; they must not appear as groups.
    table = analysis.groupby_table(df, "DIBEV_A", "SEX_A", stat="prevalence")
    values = {c.group_value for c in table.cells}
    assert values == {1, 2}
    assert 7 not in values and 9 not in values


def test_group_cap_raises_on_near_continuous_column(df):
    # WEIGHTLBTC_A has ~200 substantive values — well over the cap.
    with pytest.raises(ValueError, match="cap"):
        analysis.groupby_table(df, "DIBINS_A", "WEIGHTLBTC_A", stat="prevalence")


def test_each_cell_equals_a_direct_subpopulation_stat(df):
    # Proves no drift: each table cell is the same registry-correct weighted computation as
    # a direct per-group subpopulation_stat over `(SEX_A == v) & (DIBEV_A == 1)`.
    table = analysis.groupby_table(
        df, "DIBINS_A", "SEX_A", stat="prevalence", extra_universe="DIBEV_A == 1"
    )
    for cell in table.cells:
        direct = analysis.subpopulation_stat(
            df, "DIBINS_A",
            universe_expr=f"(SEX_A == {cell.group_value}) & (DIBEV_A == 1)",
            stat="prevalence",
        )
        assert cell.result.estimate == direct.estimate
        assert cell.result.lci == direct.lci
        assert cell.result.uci == direct.uci
        assert cell.result.unweighted_n == direct.unweighted_n


def test_cli_groupby_prints_two_row_weighted_table(df, capsys):
    args = type("A", (), {
        "variable": "DIBINS_A", "universe": "DIBEV_A == 1", "groupby": "SEX_A",
        "stat": "prevalence", "q": 0.5,
    })()
    rc = cli.cmd_analyze(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "by SEX_A" in out
    assert out.count("95% CI") == 2  # a weighted cell with a CI for each sex
    assert "SEX_A=1" in out and "SEX_A=2" in out


def test_summary_is_aggregate_table_text(df):
    table = analysis.groupby_table(
        df, "DIBINS_A", "SEX_A", stat="prevalence", extra_universe="DIBEV_A == 1"
    )
    text = table.summary()
    assert "by SEX_A" in text
    assert "WTFA_A" in text  # the survey-weighted basis
    assert "95% CI" in text and "n=" in text
    # One header line plus one line per group.
    assert len([ln for ln in text.splitlines() if ln.strip()]) == 1 + len(table.cells)
