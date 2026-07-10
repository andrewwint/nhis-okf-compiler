# Change: Root AgentCore CLI project + make nhis_okf CodeZip-packageable

## Why

The AgentCore CodeZip build packages a *self-contained* `codeLocation` dir; it cannot reach
up to the repo-root `src/` + `.okf/` (pointing it there recurses). To deploy the real agent
without a committed duplicate, `nhis_okf` must install as a dependency of a small
self-contained app project, the retrieval install must be pandas-free (CodeZip 250 MB), and
the `.okf/` bundle must be included in the built artifact. We also simplify the deploy to a
single AgentCore CLI project at the repo root and drop the CDK web front (demo is CLI-only).

**Build + local `agentcore package` smoke-test only — NO `agentcore deploy`.**

## What Changes

- **Root AgentCore CLI project; drop the web front.** The deploy is now `agentcore/` (config:
  `agentcore.json`, `aws-targets.json`) + `app/nhis_okf_chat/` (thin `main.py` + `pyproject.toml`)
  at the repo root. The hand-rolled CDK front (`deploy/infra`, `deploy/lambda`, `deploy/README.md`)
  is removed — the demo is `agentcore invoke`. `codeLocation: "app/nhis_okf_chat"`,
  `entrypoint: "main.py"`.
- **Root `pyproject.toml`:** move `pandas`/`pyarrow` to an optional `[compute]` extra; base deps
  become retrieval-only (`numpy`, `scikit-learn`, `PyYAML`). `[dev]` includes `[compute]` so
  local install/tests are unchanged (`pip install -e ".[dev]"` still full).
- **Vendored, self-contained codeLocation (no path-dep — it can't resolve at AWS runtime).**
  `app/build_runtime.py` copies `src/nhis_okf/` → `app/nhis_okf/` and `.okf/` →
  `app/nhis_okf/okf_bundle/` at package time — both **gitignored build artifacts**, guarded by a
  drift test, so `src/nhis_okf` + `.okf/` stay the sole committed source of truth. The thin
  `app/main.py` imports the vendored `nhis_okf`, sets retrieval-only mode, and re-exports the
  agent. `config.okf_dir()` falls back to the shipped `okf_bundle/` when neither `NHIS_OKF_DIR`
  nor a repo-relative `.okf/` is present.
- **Third-party-only `requirements.txt`.** `app/requirements.txt` lists only the deps AgentCore
  installs at deploy (strands-agents, bedrock-agentcore, numpy, scikit-learn, PyYAML) — no
  pandas/pyarrow, no `nhis-okf`.
- **Verify by packaging:** `agentcore package` builds the zip locally; confirm < 250 MB, contains
  the vendored code + bundle, and is pandas-free.

## Impact

- Affected specs: `okf-compiler` (MODIFIED: pandas optional extra; runtime installs nhis_okf as
  a dependency with the bundle shipped; single root CLI deploy project).
- Affected code: root `pyproject.toml`, `config.py` (bundle fallback), `agentcore/` + `app/`
  (moved to root), remove `deploy/`, `.gitignore`, `CLAUDE.md`, tests.
- Out of scope: `agentcore deploy`; Path B compute in the runtime.
