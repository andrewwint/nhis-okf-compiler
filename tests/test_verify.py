"""Verification catches the statistically-wrong concept that lint waves through."""

from nhis_okf import verify as V


def _by_id(results):
    return {r.concept_id: r for r in results}


def test_correct_concepts_pass(df, concepts):
    r = _by_id(V.verify_all(df, concepts))
    assert r["DIBEV_A"].verdict == V.PASS
    assert r["DIBINS_A"].verdict == V.PASS


def test_seeded_defect_fails(df, concepts):
    r = _by_id(V.verify_all(df, concepts))["DIBINS_A__naive"]
    assert r.verdict == V.FAIL
    assert r.delta_pp > 20  # claimed 3.66 vs correct ~31.96


def test_defect_passes_lint_but_fails_execution(df, concepts):
    """The whole thesis: a clean-linking concept caught only by executing it."""
    r = _by_id(V.verify_all(df, concepts))["DIBINS_A__naive"]
    assert r.lint.ok is True       # markdown fine, links resolve
    assert r.verdict == V.FAIL     # the number is still wrong
    assert r.caught is True


def test_diagnosis_names_both_errors(df, concepts):
    r = _by_id(V.verify_all(df, concepts))["DIBINS_A__naive"]
    joined = " ".join(r.diagnosis).lower()
    assert "unweighted" in joined
    assert "universe" in joined


def test_age_at_diagnosis_mean_verified(df, concepts):
    """DIBAGETC_A is a survey-weighted MEAN concept (years, not a %) — it must pass."""
    r = _by_id(V.verify_all(df, concepts))["DIBAGETC_A"]
    assert r.verdict == V.PASS
    assert r.kind == "mean"
    assert r.unit == "years"
    assert abs(r.correct_pct - 47.41) < 0.5


def test_wrong_mean_is_caught_while_lint_passes(df, concepts):
    """An unweighted mean is structurally clean but statistically wrong — execution catches it."""
    r = _by_id(V.verify_all(df, concepts))["DIBAGETC_A__naive"]
    assert r.lint.ok is True
    assert r.verdict == V.FAIL
    assert r.caught is True
    assert "unweighted" in " ".join(r.diagnosis).lower()
