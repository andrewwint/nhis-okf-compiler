"""The compiled bundle conforms to the OKF v0.1 spec."""

import yaml

from nhis_okf.compiler import compile_bundle, check_conformance, _split_frontmatter


def test_compiled_bundle_is_okf_conformant(df, tmp_path):
    out = tmp_path / "variables"
    compile_bundle(df, out_dir=out, log_path=tmp_path / "log.md")
    ok, issues = check_conformance(tmp_path)
    assert ok, f"OKF conformance failed: {issues}"


def test_every_concept_has_required_type_and_recommended_fields(df, tmp_path):
    out = tmp_path / "variables"
    compile_bundle(df, out_dir=out, log_path=tmp_path / "log.md")
    for p in out.glob("*.md"):
        fm = _split_frontmatter(p.read_text())
        assert fm is not None and fm.get("type")        # required
        assert "title" in fm and "description" in fm     # recommended
        assert "timestamp" in fm and isinstance(fm.get("tags"), list)


def test_reserved_files_present(df, tmp_path):
    out = tmp_path / "variables"
    compile_bundle(df, out_dir=out, log_path=tmp_path / "log.md")
    assert (tmp_path / "index.md").exists()  # progressive navigation
    assert (tmp_path / "log.md").exists()    # audit history


def test_conformance_fails_on_concept_missing_type(df, tmp_path):
    out = tmp_path / "variables"
    compile_bundle(df, out_dir=out, log_path=tmp_path / "log.md")
    # Inject a non-conforming concept (no `type`).
    (out / "BROKEN.md").write_text("---\ntitle: oops\n---\n\nno type field\n")
    ok, issues = check_conformance(tmp_path)
    assert not ok
    assert any("type" in i for i in issues)
