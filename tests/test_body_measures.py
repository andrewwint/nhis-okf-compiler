"""Whole-sample continuous body-measure concepts and their seeded raw-code defects."""

from nhis_okf import registry, verify as verify_mod, analysis
from nhis_okf.concepts import load_all


def _by_id(results):
    return {r.concept_id: r for r in results}


def test_registry_body_measures_are_whole_sample():
    for name, hi in (("WEIGHTLBTC_A", 300), ("HEIGHTTC_A", 77)):
        var = registry.get(name)
        assert var.universe_expr is None  # asked of all sample adults, no skip-pattern
        assert var.weight == "WTFA_A"
        assert max(var.valid_codes) == hi - 1


def test_body_measure_means_verify(df, concepts):
    results = _by_id(verify_mod.verify_all(df, concepts))
    for cid, val in (("WEIGHTLBTC_A", 178.53), ("HEIGHTTC_A", 66.82)):
        r = results[cid]
        assert r.verdict == verify_mod.PASS
        assert abs(r.correct_pct - val) < 0.5
        assert r.kind == "mean"


def test_rawcode_defects_are_caught(df, concepts):
    results = _by_id(verify_mod.verify_all(df, concepts))
    for cid in ("WEIGHTLBTC_A__rawcodes", "HEIGHTTC_A__rawcodes"):
        r = results[cid]
        assert r.verdict == verify_mod.FAIL
        assert r.caught is True  # clean markdown + resolving link — caught by executing
        assert r.seeded_defect is True
        # The claim (retaining top-codes) is materially above the registry-correct mean.
        assert r.claimed_pct > r.correct_pct


def test_sex_stratified_subpopulation_returns_aggregate(df):
    male = analysis.subpopulation_stat(
        df, "WEIGHTLBTC_A", universe_expr="SEX_A == 1", stat="mean"
    )
    female = analysis.subpopulation_stat(
        df, "WEIGHTLBTC_A", universe_expr="SEX_A == 2", stat="mean"
    )
    # Distinct subgroup weighted means, and only an aggregate is exposed (no raw rows).
    assert abs(male.estimate - female.estimate) > 5
    assert isinstance(male.estimate, float) and male.unweighted_n > 0
    assert not hasattr(male, "rows")
