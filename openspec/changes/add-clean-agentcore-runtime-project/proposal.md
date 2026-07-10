# Change: Clean AgentCore CLI runtime project (CodeZip, retrieval-only) + build

## Why

The deploy needs a proper AgentCore CLI runtime project (`agentcore.json` + `app/main.py` +
`requirements.txt`) — the supported `agentcore deploy` path — but the previous one (`nhisokf/`,
deleted) reimplemented the agent and drifted. Recreate it **clean** under `deploy/agentcore/`:
a thin `main.py` that imports the real `src/nhis_okf/agentcore_app.py`, packaged as a **CodeZip,
retrieval-only** runtime (fastest to a live agent, fits the 250 MB CodeZip limit). Two small
enablers are required in `src/nhis_okf`: the retrieval path must not drag in pandas, and the
bundle location must be overridable so the packaged runtime finds its shipped `.okf/`.

**Build + local smoke-test only — this change does NOT run `agentcore deploy`.**

## What Changes

- **Retrieval-only is pandas-free.** In `chat.py`, lazy-import `analysis` (only inside the
  compute tools) so importing the agent for retrieval does not require pandas/pyarrow. Add a
  retrieval-only tool mode (env `NHIS_RUNTIME_TOOLS=retrieval`): the agent registers only
  `search_verified_okf`. The full 3-tool agent is unchanged locally.
- **Bundle path override.** `compiler.OKF_DIR` (used by retrieval) resolves via `NHIS_OKF_DIR`
  (default `<repo>/.okf`), so the packaged runtime can point at its bundled copy. Repo-relative
  default keeps local/tests unchanged.
- **Clean CLI project under `deploy/agentcore/`.** `agentcore.json` (build CodeZip, protocol
  HTTP, entrypoint `app/main.py`, Python 3.12), `aws-targets.json`, `app/main.py` (thin:
  re-export `nhis_okf.agentcore_app.app`, set retrieval-only mode + `NHIS_OKF_DIR` to the
  bundled `.okf/`), and the existing retrieval-only `requirements.txt`. Generated CLI artifacts
  (`cdk/`, `.cache/`, `node_modules/`, `.venv/`) are gitignored — never committed.
- **Package assembly + smoke test.** A documented step assembles the CodeZip contents
  (`src/nhis_okf` + `.okf/`) and locally verifies the retrieval-only agent imports and answers
  without pandas.

## Impact

- Affected specs: `okf-compiler` (ADDED: retrieval-only runtime mode + bundle path override +
  the CLI runtime project).
- Affected code: `chat.py` (lazy analysis, retrieval-only mode), `compiler.py`/`config.py`
  (`NHIS_OKF_DIR`), new `deploy/agentcore/` project, `.gitignore`, tests.
- Out of scope: `agentcore deploy` (separate gated step); Path B container/compute; the
  `deploy/infra`+`deploy/lambda` web front (unchanged).
