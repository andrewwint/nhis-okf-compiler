# Tasks: nhis_okf CodeZip packaging (pip dep, pandas optional)

NO AWS beyond local `agentcore package`. Keep local install/tests + all invariants intact.

## 1. pandas becomes an optional extra
- [ ] 1.1 Root `pyproject.toml`: base `dependencies` = numpy, scikit-learn, PyYAML. Add `[project.optional-dependencies]` `compute = ["pandas>=2.0","pyarrow>=14.0"]`; make `dev` include compute + pytest.
- [ ] 1.2 Verify `import nhis_okf.agentcore_app` (retrieval path) works with ONLY the base deps installed (no pandas). The compute tools already lazy-import analysis.
- [ ] 1.3 Local `./.venv/bin/pip install -e ".[dev]"` still yields the full env; all 100 tests pass.

## 2. Ship the .okf bundle + fallback
- [ ] 2.1 Include `.okf/` in the built `nhis_okf` artifact — prefer setuptools force-include into the wheel as package data; if not clean, a package-time copy into the gitignored codeLocation. No committed duplicate of the bundle.
- [ ] 2.2 `config.okf_dir()`: resolve NHIS_OKF_DIR → repo-relative `.okf/` (if exists) → the shipped/packaged bundle location. Repo-relative default unchanged locally.
- [ ] 2.3 Test the fallback resolves to the shipped bundle when repo `.okf/` is absent and env unset (simulate).

## 3. Self-contained app project
- [ ] 3.1 `deploy/agentcore/app/pyproject.toml`: name, requires-python, deps = the local `nhis-okf` (base) + bedrock-agentcore + strands-agents + aws-opentelemetry-distro; `[tool.uv.sources]` nhis-okf = path to repo root (non-editable). main.py unchanged (thin shim; sets NHIS_RUNTIME_TOOLS=retrieval + NHIS_OKF_DIR).
- [ ] 3.2 `.gitignore`: ignore any package-time bundle copy / build staging under `deploy/agentcore/`.

## 4. Package + smoke test (NO deploy)
- [ ] 4.1 Run `agentcore package` from `deploy/agentcore/`; it must SUCCEED. Report the built zip size (must be < 250 MB) and confirm the installed set is retrieval-only (grep the staging for pandas — must be absent).
- [ ] 4.2 Import the packaged app / the base-install agent and exercise a grounded answer + refusal (retrieval-only). Capture output.

## 5. Closeout
- [ ] 5.1 `./.venv/bin/pytest -q` green (100 + any new). `nhis verify`/`trends`/`compile`/`conformance` unchanged; `.okf/` byte-unchanged.
- [ ] 5.2 `openspec validate package-nhis-okf-for-codezip --strict` passes.
- [ ] 5.3 Update checkboxes; report the packaged zip size + whether it fits CodeZip, and a GO/NO-GO for `agentcore deploy`.
