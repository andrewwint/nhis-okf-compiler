"""Hypertension: a second condition proving the pattern generalizes with no engine change."""

from nhis_okf import analysis, verify as V


def _by_id(results):
    return {r.concept_id: r for r in results}


def test_hypertension_prevalence_weighted(df):
    r = analysis.correct_prevalence(df, "HYPEV_A")
    assert abs(r.value_pct - 32.26) < 0.5


def test_bp_med_among_diagnosed_universe_correct(df):
    r = analysis.correct_prevalence(df, "HYPMED_A", analytical_universe="HYPEV_A == 1")
    assert abs(r.value_pct - 79.62) < 0.5
    assert r.denominator_unweighted < 12000  # the diagnosed subgroup, not the whole sample


def test_seeded_bp_med_defect_is_caught(df, concepts):
    r = _by_id(V.verify_all(df, concepts))["HYPMED_A__naive"]
    assert r.verdict == V.FAIL
    assert r.lint.ok and r.caught          # clean markdown; caught only by executing
    assert r.delta_pp > 40                 # ~49pp off (whole-sample, unweighted)


def test_both_conditions_pass_their_correct_concepts(df, concepts):
    r = _by_id(V.verify_all(df, concepts))
    assert r["HYPEV_A"].verdict == V.PASS
    assert r["HYPMED_A"].verdict == V.PASS
    assert r["DIBINS_A"].verdict == V.PASS  # diabetes still passes — no regression
