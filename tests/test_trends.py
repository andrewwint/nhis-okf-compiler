"""Cross-year trends: the 2019 redesign-rename catch."""

import pytest

from nhis_okf import trends, registry
from nhis_okf.compiler import compile_bundle, check_conformance


@pytest.fixture(scope="session")
def trend_data():
    missing = [y for y in registry.YEAR_FILES if not trends.year_csv(y).exists()]
    if missing:
        pytest.skip(f"missing year data {missing}; run `nhis fetch`")


def _by_id(results):
    return {r.concept_id: r for r in results}


def test_correct_trend_passes_with_rename_aware_values(trend_data):
    r = _by_id(trends.verify_all_trends())["TREND_diabetes_2018_2023"]
    assert r.verdict == trends.PASS
    assert abs(r.correct[2018] - 10.09) < 0.3
    assert abs(r.correct[2023] - 9.80) < 0.3


def test_naive_single_name_join_is_caught(trend_data):
    r = _by_id(trends.verify_all_trends())["TREND_diabetes__naive"]
    assert r.verdict == trends.FAIL
    assert r.caught is True  # clean markdown, resolving link — caught only by executing
    joined = " ".join(r.diagnosis).lower()
    assert "2018" in joined and ("renamed" in joined or "redesign" in joined)


def test_each_name_is_absent_in_the_other_year(trend_data):
    cols18 = trends._columns_for_year(2018)
    cols23 = trends._columns_for_year(2023)
    assert "DIBEV_A" not in cols18  # the rename gap, both directions
    assert "DIBEV1" not in cols23


def test_bmi_recode_join_is_caught_with_scale_mismatch(trend_data):
    r = _by_id(trends.verify_all_trends())["TREND_bmi__naive"]
    assert r.verdict == trends.FAIL
    assert r.caught is True  # both columns exist, link resolves — caught only by executing
    assert r.seeded_defect is True
    joined = " ".join(r.diagnosis).lower()
    assert "scale/units mismatch" in joined
    assert "continuous" in joined and "categorical" in joined
    # The guard short-circuits before the prevalence value path (no correct series computed).
    assert r.correct == {}


def test_valid_diabetes_trend_not_flagged_by_encoding_guard(trend_data):
    # A compatible rename (categorical->categorical, overlapping) must NOT be flagged.
    from nhis_okf.trends import _encoding_incompatible, load_trends
    good = {c.id: c for c in load_trends()}["TREND_diabetes_2018_2023"]
    assert _encoding_incompatible(good) == []


def test_compile_writes_verified_trend_and_quarantines_naive(df, trend_data, tmp_path):
    out = tmp_path / "variables"
    report = compile_bundle(df, out_dir=out, log_path=tmp_path / "log.md")
    assert report.ok is True
    assert "TREND_diabetes_2018_2023" in report.trend_written
    assert "TREND_diabetes__naive" in report.trend_quarantined
    assert (out / "TREND_diabetes_2018_2023.md").exists()
    assert not (out / "TREND_diabetes__naive.md").exists()
    # The trend bundle still conforms to OKF v0.1.
    ok, issues = check_conformance(tmp_path)
    assert ok, issues
