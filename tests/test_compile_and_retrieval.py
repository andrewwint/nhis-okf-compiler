"""The bundle is verified by construction, and the quarantined number is unreachable.

Tests compile into a temporary directory (via tmp_path) so running the suite never
dirties the committed `.okf/` artifact.
"""

import pytest

from nhis_okf.compiler import compile_bundle
from nhis_okf.retrieval import Retriever
from nhis_okf.chat import answer


@pytest.fixture
def bundle(df, tmp_path):
    out = tmp_path / "variables"
    report = compile_bundle(df, out_dir=out, log_path=tmp_path / "log.md")
    return report, out


def test_compile_quarantines_defect_and_keeps_invariant(bundle):
    report, out = bundle
    assert report.ok is True
    assert "DIBINS_A__naive" in report.quarantined
    assert "DIBINS_A" in report.written
    assert not (out / "DIBINS_A__naive.md").exists()


def test_naive_number_is_not_anywhere_in_the_bundle(bundle):
    _, out = bundle
    blob = "\n".join(p.read_text() for p in out.glob("*.md"))
    assert "31.96" in blob          # the verified number is present
    assert "3.66" not in blob       # the quarantined naive number is not


def test_retrieval_returns_verified_insulin_concept(bundle):
    _, out = bundle
    r = Retriever.from_bundle(out)
    hits = r.search("how many adults with diabetes take insulin?", k=3)
    assert hits
    assert hits[0].concept.id == "DIBINS_A"


def test_query_serves_verified_number_with_citation_and_safety(bundle):
    _, out = bundle
    r = Retriever.from_bundle(out)
    # generative=False keeps the test hermetic (no network / no model call).
    ans = answer(
        "what share of adults with diabetes take insulin?",
        retriever=r,
        generative=False,
    )
    assert ans.mode == "extractive"
    assert "31.96" in ans.text
    assert "3.66" not in ans.text            # cannot serve the quarantined figure
    assert "not medical advice" in ans.text  # safety framing always present
    assert any("DIBINS_A" in c for c in ans.citations)
