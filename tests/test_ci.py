"""Design-based confidence intervals (Taylor linearization) and the over-precise-CI catch."""

from nhis_okf import analysis, verify as V


def _by_id(results):
    return {r.concept_id: r for r in results}


def test_ci_point_matches_weighted_estimate(df):
    ci = analysis.correct_ci(df, "DIBEV_A")
    pt = analysis.correct_prevalence(df, "DIBEV_A")
    assert abs(ci.estimate_pct - pt.value_pct) < 1e-6


def test_design_effect_exceeds_one(df):
    """The correctness property: clustering inflates variance, so DEFF > 1."""
    for var, uni in [("DIBEV_A", None), ("DIBINS_A", "DIBEV_A == 1"),
                     ("HYPMED_A", "HYPEV_A == 1")]:
        ci = analysis.correct_ci(df, var, analytical_universe=uni)
        assert ci.deff > 1.0, f"{var} DEFF={ci.deff}"


def test_ci_brackets_the_estimate(df):
    ci = analysis.correct_ci(df, "DIBINS_A", analytical_universe="DIBEV_A == 1")
    assert ci.lci_pct < ci.estimate_pct < ci.uci_pct
    assert ci.se_pp > 0


def test_design_ci_is_wider_than_srs(df):
    """A design-based interval must be at least as wide as the naive SRS interval."""
    import numpy as np
    ci = analysis.correct_ci(df, "DIBEV_A")
    n = analysis.correct_prevalence(df, "DIBEV_A").denominator_unweighted
    p = ci.estimate_pct / 100
    srs_hw = 1.96 * np.sqrt(p * (1 - p) / n) * 100
    design_hw = (ci.uci_pct - ci.lci_pct) / 2
    assert design_hw > srs_hw


def test_verified_concepts_carry_a_ci(df, concepts):
    r = _by_id(V.verify_all(df, concepts))["DIBINS_A"]
    assert r.verdict == V.PASS
    assert r.ci is not None and r.ci.lci_pct < r.ci.estimate_pct < r.ci.uci_pct


def test_over_precise_ci_is_caught(df, concepts):
    """Point estimate correct, but an SRS-style CI that ignores the design effect is caught."""
    r = _by_id(V.verify_all(df, concepts))["DIBEV_A__tightci"]
    assert r.verdict == V.FAIL
    assert r.delta_pp == 0.0          # the point estimate is right
    assert r.lint.ok and r.caught     # caught only by executing the design-based variance
    assert any("design effect" in d.lower() for d in r.diagnosis)
