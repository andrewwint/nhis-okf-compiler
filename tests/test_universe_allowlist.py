"""The `injection-sink@universe-eval` seam: `analysis.validate_universe` is the allow-list
gate an AGENT-supplied universe must pass before it can reach `_mask`'s `df.eval`.

Grammar permitted (and nothing wider):

    expr       := term (('&' | '|') term)*
    term       := '(' expr ')' | comparison
    comparison := COLUMN <op> NUMBER          op in  ==  !=  >=  <=  >  <

Every identifier must be a real data column. These tests prove (a) every existing
repo/CLI/concept universe still parses, and (b) a representative injection set is rejected
with a clear ValueError and never evaluated. An independent security-review lane audits this.
"""

import pytest

from nhis_okf import analysis

# The identifiers a universe may name — validated against the real columns, not hardcoded in
# the validator. Mirrors the slice columns the agent path would allow.
COLUMNS = {
    "DIBEV_A", "DIBINS_A", "DIBPILL_A", "PREDIB_A", "SEX_A", "HYPEV_A", "HYPMED_A",
    "WEIGHTLBTC_A", "HEIGHTTC_A", "BMICAT_A", "DIBAGETC_A",
}


# --- Every existing universe must still parse (must not break CLI/concept universes) ------

@pytest.mark.parametrize(
    "expr",
    [
        "DIBEV_A == 1",
        "(DIBEV_A == 1) | (PREDIB_A == 1)",
        "SEX_A == 2",
        "DIBEV_A == 1 & SEX_A == 2",
        "DIBEV_A == 999",
        "(SEX_A == 1) & (DIBEV_A == 1)",       # groupby-assembled universe
        "HYPEV_A == 1",
        "DIBEV_A != 2",
        "WEIGHTLBTC_A >= 100",
        None,                                   # None == "all rows", a no-op
    ],
)
def test_valid_universe_passes(expr):
    # Passes the gate without raising (does not evaluate anything).
    analysis.validate_universe(expr, COLUMNS)


def test_valid_universes_still_evaluate_identically(df):
    """The gate is a no-op on valid input: the mask matches the un-gated df.eval exactly."""
    for expr in ["DIBEV_A == 1", "(DIBEV_A == 1) | (PREDIB_A == 1)", "DIBEV_A == 1 & SEX_A == 2"]:
        analysis.validate_universe(expr, set(df.columns))  # must not raise
        assert analysis._mask(df, expr).equals(df.eval(expr))


# --- A representative injection set is rejected, and NEVER evaluated ----------------------

@pytest.mark.parametrize(
    "expr",
    [
        "DIBEV_A.__class__",            # attribute access
        "@__import__('os')",           # import / illegal char
        "SEX_A == 1 or eval('1')",     # a call + string literal + keyword
        "DIBEV_A",                     # a bare name (no comparison)
        "foo(1)",                      # a function call on an unknown name
        "__import__",                  # a dunder identifier
        "DIBEV_A == 1; import os",     # statement separator / import
        "SEX_A == '1'",                # string literal comparator
        "DIBEV_A == 1 and SEX_A == 2", # python boolean keyword (not & |)
        "AGEP_A > 40",                 # a name that is not a known column
        "DIBEV_A == 1)",               # unbalanced parenthesis
        "1 == 1",                      # no column
    ],
)
def test_injection_universe_is_rejected(expr):
    with pytest.raises(ValueError, match="universe rejected|must be a string"):
        analysis.validate_universe(expr, COLUMNS)


def test_rejected_injection_never_reaches_df_eval(df, monkeypatch):
    """A rejected universe raises BEFORE any df.eval could run."""
    called = {"n": 0}
    real_eval = df.eval

    def _spy(expr, *a, **k):
        called["n"] += 1
        return real_eval(expr, *a, **k)

    monkeypatch.setattr(df, "eval", _spy, raising=False)
    with pytest.raises(ValueError):
        analysis.validate_universe("DIBEV_A.__class__", set(df.columns))
    assert called["n"] == 0  # nothing was evaluated
