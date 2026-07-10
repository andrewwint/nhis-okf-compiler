# Tasks: nhis_okf CodeZip packaging (pip dep, pandas optional)

NO AWS beyond local `agentcore package`. Keep local install/tests + all invariants intact.

## 1. pandas becomes an optional extra
- [x] 1.1 Root `pyproject.toml`: base `dependencies` = numpy, scikit-learn, PyYAML. Add `[project.optional-dependencies]` `compute = ["pandas>=2.0","pyarrow>=14.0"]`; make `dev` include compute + pytest.
- [x] 1.2 Verify the retrieval path works with ONLY the base deps installed (no pandas) — confirmed in a base-only scratch venv: grounded answer + refusal, `pandas`/`nhis_okf.analysis` never imported.
- [x] 1.3 Local `./.venv/bin/pip install -e ".[dev]"` still yields the full env (pandas 3.0.3, pyarrow 24.0.0); all tests pass.

## 2. Ship the .okf bundle + fallback
- [x] 2.1 `.okf/` is vendored into the codeLocation (`app/nhis_okf/okf_bundle/`) by `app/build_runtime.py` — a gitignored build artifact, no committed duplicate. (Wheel force-include was abandoned: the CodeZip installs no `nhis_okf` wheel; the package is vendored.)
- [x] 2.2 `config.okf_dir()`: resolve NHIS_OKF_DIR → repo-relative `.okf/` (if exists) → the shipped bundle (`_shipped_bundle_dir()` = the vendored `okf_bundle/` beside `config.py`). Repo-relative default unchanged locally.
- [x] 2.3 Test the fallback resolves to the shipped bundle when repo `.okf/` is absent and env unset (`test_okf_dir_falls_back_to_shipped_bundle`).

## 3. Self-contained app project (vendored, not a path-dep)
- [x] 3.1 `app/build_runtime.py` vendors `src/nhis_okf/` → `app/nhis_okf/` + `.okf/` → `app/nhis_okf/okf_bundle/`; `app/requirements.txt` = third-party only (strands, bedrock-agentcore, numpy, scikit-learn, PyYAML — NO pandas/pyarrow/nhis-okf). `app/main.py` imports the vendored package, sets NHIS_RUNTIME_TOOLS=retrieval + NHIS_OKF_DIR. (uv path-dep dropped — it cannot resolve at AWS runtime.)
- [x] 3.2 `.gitignore`: ignores the vendored build artifact `app/nhis_okf/`.

## 4. Package + smoke test (NO deploy)
- [x] 4.1 `agentcore package` SUCCEEDS: `agentcore/nhis_okf_chat.zip` = 58 MB (< 250 MB). Zip contains `nhis_okf/*.py` + `nhis_okf/okf_bundle/` + `main.py` + `requirements.txt`; `pandas`/`pyarrow` ABSENT.
- [x] 4.2 Exercised the vendored package (retrieval-only, base deps): grounded answer returns 31.96% with weighted basis + CI; off-bundle query never fabricates (no 3.66%); pandas/analysis never loaded.

## 5. Closeout
- [x] 5.1 `./.venv/bin/pytest -q` green (102: 100 + okf_dir-fallback + vendor-drift-guard). `nhis conformance` PASS; `.okf/` byte-unchanged (verify/trends/compile modules untouched).
- [x] 5.2 `openspec validate package-nhis-okf-for-codezip --strict` passes.
- [x] 5.3 Checkboxes updated; zip 58 MB fits CodeZip; GO/NO-GO reported below.
