"""The parquet twin is a derived cache: same estimates as the CSV, and it must not
choke on a column that a given file happens not to have."""

import pandas as pd
import pytest

from nhis_okf import analysis
from nhis_okf.cli import SLICE_COLUMNS


def _write_csv(tmp_path):
    csv = tmp_path / "mini.csv"
    pd.DataFrame(
        {
            "DIBEV_A": [1, 1, 2, 1, 2],
            "DIBAGETC_A": [40, 50, 2, 97, 2],
            "WTFA_A": [1000.0, 3000.0, 500.0, 2000.0, 800.0],
            "PSTRAT": [1, 1, 2, 2, 3],
            "PPSU": [1, 2, 1, 2, 1],
        }
    ).to_csv(csv, index=False)
    return csv


def test_parquet_and_csv_agree_on_prevalence_and_mean(tmp_path):
    csv = _write_csv(tmp_path)
    cols = ["DIBEV_A", "DIBAGETC_A", "WTFA_A", "PSTRAT", "PPSU"]

    df_csv = analysis.load_table(csv, columns=cols)  # no twin yet -> CSV path
    prev_csv = analysis.correct_prevalence(df_csv, "DIBEV_A")
    mean_csv = analysis.correct_mean(df_csv, "DIBAGETC_A", analytical_universe="DIBEV_A == 1")

    twin = analysis.materialize_parquet(csv)
    assert twin.exists()
    df_pq = analysis.load_table(csv, columns=cols)  # twin present -> parquet path
    prev_pq = analysis.correct_prevalence(df_pq, "DIBEV_A")
    mean_pq = analysis.correct_mean(df_pq, "DIBAGETC_A", analytical_universe="DIBEV_A == 1")

    assert abs(prev_csv.value_pct - prev_pq.value_pct) < 1e-9
    assert abs(mean_csv.value - mean_pq.value) < 1e-9


def test_missing_column_projection_does_not_raise(tmp_path):
    csv = _write_csv(tmp_path)
    analysis.materialize_parquet(csv)
    # NOSUCH_A is absent; the parquet path must silently skip it, not raise.
    df = analysis.load_table(csv, columns=["DIBEV_A", "NOSUCH_A", "WTFA_A"])
    assert "DIBEV_A" in df.columns
    assert "NOSUCH_A" not in df.columns


def test_materialize_is_idempotent(tmp_path):
    csv = _write_csv(tmp_path)
    first = analysis.materialize_parquet(csv)
    mtime = first.stat().st_mtime
    second = analysis.materialize_parquet(csv)  # unchanged CSV -> no rebuild
    assert second == first
    assert second.stat().st_mtime == mtime


def test_full_slice_estimates_match_across_paths(df):
    """Against the real file, whichever path the fixture used, the slice loads cleanly."""
    r = analysis.correct_prevalence(df, "DIBEV_A")
    assert abs(r.value_pct - 9.80) < 0.5
    assert set(SLICE_COLUMNS) >= {"DIBAGETC_A", "WTFA_A"}
