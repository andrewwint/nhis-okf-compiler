# Tasks: clean AgentCore CLI runtime project (CodeZip, retrieval-only)

NO AWS (build + smoke-test only). One agent (`src/nhis_okf`), one bundle (`.okf/`). Preserve
all existing behavior/tests, the aggregate-only / grounded-or-refuse / agent-boundary invariants.

## 1. Retrieval-only path is pandas-free
- [x] 1.1 `chat.py`: move `from . import analysis` to lazy imports inside `_microdata`/`analyze_subpopulation`/`groupby_table`, so importing chat for retrieval does NOT import pandas/analysis. `config` stays a normal import.
- [x] 1.2 Retrieval-only tool mode: `_as_tools()` returns only `search_verified_okf` when `NHIS_RUNTIME_TOOLS=retrieval` (default = all three tools). No behavior change locally.
- [x] 1.3 Test: with `NHIS_RUNTIME_TOOLS=retrieval`, the built agent has only the retrieval tool; and importing the retrieval path does not require pandas (e.g. assert `analysis` not needed — simulate by checking the tool set / a lazy-import unit test).

## 2. Bundle path override
- [x] 2.1 `config.okf_dir()` reads env `NHIS_OKF_DIR` (default `<repo>/.okf`); route `compiler.OKF_DIR`/`VARIABLES_DIR` (which retrieval consumes) through it. Repo-relative default unchanged.
- [x] 2.2 Test: setting `NHIS_OKF_DIR` to an alternate dir redirects retrieval; unset = current behavior. Existing tests still green.

## 3. Clean CLI project under deploy/agentcore/
- [x] 3.1 `deploy/agentcore/agentcore.json`: build `CodeZip`, protocol `HTTP`, entrypoint `app/main.py`, `runtimeVersion` `PYTHON_3_12`, a sensible runtime name; codeLocation set so the CodeZip includes `src/nhis_okf/` + `.okf/` (per deploy/README).
- [x] 3.2 `deploy/agentcore/aws-targets.json` (empty/placeholder targets), and keep/refresh `deploy/agentcore/requirements.txt` (retrieval-only: strands-agents, bedrock-agentcore, scikit-learn, numpy, PyYAML — NO pandas).
- [x] 3.3 `deploy/agentcore/app/main.py`: thin — set `NHIS_RUNTIME_TOOLS=retrieval` and `NHIS_OKF_DIR` to the bundled `.okf/`, then `from nhis_okf.agentcore_app import app`. No agent logic.
- [x] 3.4 `.gitignore`: ignore `deploy/agentcore/{cdk/,.cache/,node_modules/,.venv/,.env.local}` so generated/heavy/secret files never commit.

## 4. Package assembly + local smoke test (NO AWS)
- [x] 4.1 Document (in deploy/README or a short note) how the CodeZip is assembled to include `src/nhis_okf` + `.okf/`, and how `NHIS_OKF_DIR` points the runtime at the bundled bundle.
- [x] 4.2 Local smoke test: import `deploy/agentcore/app/main.py`'s app in retrieval-only mode with `NHIS_OKF_DIR` set to `.okf/`; exercise a grounded query + a refusal WITHOUT pandas installed-or-imported on that path (or assert pandas isn't imported). If `bedrock_agentcore`/`strands` aren't importable locally, test `chat.answer` retrieval-only path directly and note the limitation. Do NOT run `agentcore deploy`; `agentcore validate` only if it needs no AWS.

## 5. Closeout
- [x] 5.1 `./.venv/bin/pytest -q` green (existing 89 + new mode/override tests). `nhis verify`/`trends`/`compile`/`conformance` unchanged; `.okf/` byte-unchanged.
- [x] 5.2 `openspec validate add-clean-agentcore-runtime-project --strict` passes.
- [x] 5.3 Update checkboxes; report what is smoke-tested vs. what only the real deploy confirms (package size, cold start, live invoke).
