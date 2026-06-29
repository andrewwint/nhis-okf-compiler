"""The statistics must be right: weighted, universe-correct, and not the naive number."""

from nhis_okf import analysis, registry


def test_weighted_diabetes_prevalence(df):
    r = analysis.correct_prevalence(df, "DIBEV_A")
    assert r.weighted is True
    assert abs(r.value_pct - 9.80) < 0.3


def test_insulin_among_diagnosed_is_weighted_and_universe_correct(df):
    r = analysis.correct_prevalence(df, "DIBINS_A", analytical_universe="DIBEV_A == 1")
    assert abs(r.value_pct - 31.96) < 0.5
    # The universe is the diagnosed, not the whole sample.
    assert r.denominator_unweighted < 4000


def test_naive_method_is_far_from_correct(df):
    """The whole-sample figure (missing treated as 'no') is wrong by a wide margin."""
    naive = analysis.compute_prevalence(
        df, "DIBINS_A", universe_expr=None,
        affirmative_codes=(1,), valid_codes=(1, 2), weighted=False,
        denominator="all_in_universe",
    )
    correct = analysis.correct_prevalence(
        df, "DIBINS_A", analytical_universe="DIBEV_A == 1"
    )
    assert abs(naive.value_pct - 3.66) < 0.5
    assert abs(correct.value_pct - naive.value_pct) > 20  # ~28pp apart


def test_weighting_changes_the_population_estimate(df):
    """Weighting is not cosmetic: for diabetes prevalence the weighted population
    estimate (~9.8%) differs from the raw sample share (~11.2%)."""
    w = analysis.compute_prevalence(
        df, "DIBEV_A", universe_expr=None,
        affirmative_codes=(1,), valid_codes=(1, 2), weighted=True,
    )
    u = analysis.compute_prevalence(
        df, "DIBEV_A", universe_expr=None,
        affirmative_codes=(1,), valid_codes=(1, 2), weighted=False,
    )
    assert abs(w.value_pct - u.value_pct) > 0.5


def test_registry_weight_is_mandatory():
    assert registry.get("DIBINS_A").weight == registry.SAMPLE_ADULT_WEIGHT
