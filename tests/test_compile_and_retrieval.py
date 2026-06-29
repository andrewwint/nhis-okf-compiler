"""The bundle is verified by construction, and the quarantined number is unreachable."""

from nhis_okf.compiler import compile_bundle, VARIABLES_DIR
from nhis_okf.retrieval import Retriever
from nhis_okf.chat import answer


def test_compile_quarantines_defect_and_keeps_invariant(df):
    report = compile_bundle(df)
    assert report.ok is True
    assert "DIBINS_A__naive" in report.quarantined
    assert "DIBINS_A" in report.written
    # The defect concept file is not in the trusted bundle.
    assert not (VARIABLES_DIR / "DIBINS_A__naive.md").exists()


def test_naive_number_is_not_anywhere_in_the_bundle(df):
    compile_bundle(df)
    blob = "\n".join(p.read_text() for p in VARIABLES_DIR.glob("*.md"))
    assert "31.96" in blob          # the verified number is present
    assert "3.66" not in blob       # the quarantined naive number is not


def test_retrieval_returns_verified_insulin_concept(df):
    compile_bundle(df)
    r = Retriever.from_bundle()
    hits = r.search("how many adults with diabetes take insulin?", k=3)
    assert hits
    assert hits[0].concept.id == "DIBINS_A"


def test_query_serves_verified_number_with_citation_and_safety(df):
    compile_bundle(df)
    ans = answer("what share of adults with diabetes take insulin?")
    assert "31.96" in ans.text
    assert "3.66" not in ans.text            # cannot serve the quarantined figure
    assert "not medical advice" in ans.text  # safety framing always present
    assert any("DIBINS_A" in c for c in ans.citations)
