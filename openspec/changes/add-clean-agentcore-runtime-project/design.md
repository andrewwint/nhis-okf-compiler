## Context

We consolidated on `deploy/` and want the supported `agentcore deploy` flow: an AgentCore CLI
project with a thin `app/main.py` importing the real agent. The deploy is CodeZip retrieval-only
(fastest, fits 250 MB). Two `src` enablers make that clean.

## Goals / Non-Goals

- Goals: a clean, committed AgentCore CLI project under `deploy/agentcore/`; a retrieval-only,
  pandas-free runtime path; a bundle-path override so the packaged runtime finds `.okf/`;
  everything smoke-tested locally.
- Non-Goals: running `agentcore deploy`; Path B container/compute; touching the web front.

## Decisions

- **Thin entrypoint, not a reimplementation.** `app/main.py` re-exports
  `nhis_okf.agentcore_app.app`. The agent stays the reviewed single source of truth.
- **Retrieval-only via lazy imports + a tool-mode flag.** The compute tools import pandas
  lazily, and `NHIS_RUNTIME_TOOLS=retrieval` registers only `search_verified_okf`. So the
  CodeZip carries sklearn/numpy (retrieval) but not pandas/pyarrow — smaller, and no drift from
  the local agent (same module, fewer tools).
- **Bundle path via env override.** `NHIS_OKF_DIR` lets the packaged runtime point at its
  bundled `.okf/`; repo-relative default keeps local unchanged. This is the minimal indirection
  the runtime needs (retrieval reads the bundle; no parquet in retrieval-only).
- **Generated CLI artifacts are gitignored.** The prior project committed `cdk/`, `.cache`,
  `.venv`, `node_modules` — the mess we removed. Ignore them here so only the hand-authored
  config + thin shim + requirements are tracked.

## Risks / Trade-offs

- CodeZip size with sklearn → measured in the smoke test; if near 250 MB, options are dropping
  sklearn for the pure-Python cosine (later) or the container path. Not a blocker for build.
- Local smoke test may lack `bedrock_agentcore`/`strands` (deploy-only) → fall back to testing
  `chat.answer` retrieval-only and assert the pandas-free property directly.

## Migration Plan

Additive: new deploy project + two small backward-compatible `src` enablers. Defaults preserve
all current behavior. The actual deploy is a later gated step.

## Open Questions

- Exact `codeLocation`/packaging mechanics for including `src/nhis_okf` + `.okf/` in the CodeZip
  — documented in the smoke test; confirmed for real only at `agentcore deploy` time.
