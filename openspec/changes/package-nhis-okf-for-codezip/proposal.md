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
- **Bundle shipping:** include `.okf/` in the built artifact — as `nhis_okf` package data
  (setuptools force-include) if clean, else a package-time copy into the gitignored codeLocation.
  No committed duplicate. `config.okf_dir()` falls back to the shipped bundle when the
  repo-relative `.okf/` is absent and `NHIS_OKF_DIR` is unset.
- **Self-contained app:** `app/nhis_okf_chat/pyproject.toml` depends on `nhis-okf` (base,
  pandas-free) + the AgentCore/Strands runtime deps via a `uv` path source to the repo root; the
  thin `main.py` sets retrieval-only mode + `NHIS_OKF_DIR` and re-exports the agent.
- **Verify by packaging:** `agentcore package` builds the zip locally; confirm < 250 MB, imports
  retrieval-only (no pandas), and finds the bundle.

## Impact

- Affected specs: `okf-compiler` (MODIFIED: pandas optional extra; runtime installs nhis_okf as
  a dependency with the bundle shipped; single root CLI deploy project).
- Affected code: root `pyproject.toml`, `config.py` (bundle fallback), `agentcore/` + `app/`
  (moved to root), remove `deploy/`, `.gitignore`, `CLAUDE.md`, tests.
- Out of scope: `agentcore deploy`; Path B compute in the runtime.
