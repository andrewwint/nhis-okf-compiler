# Change: Consolidate the deploy on `deploy/`; remove the duplicate `nhisokf/`

## Why

The repo carried two overlapping AgentCore deploy trees. `deploy/` is the intended, documented
stack — a CDK app (Lambda Function URL + Turnstile CAPTCHA + rate caps + budget alarm) that runs
**the real agent** `src/nhis_okf/agentcore_app.py` (`deploy/README.md:47-48`). `nhisokf/` was an
abandoned `agentcore`-CLI scaffold whose `app/nhisokf/main.py` **reimplemented** the grounded
agent from scratch and shipped its **own stale copy** of the OKF bundle (8 concepts vs the
canonical 10). Nothing outside `nhisokf/` referenced it. Two agents and two bundles guarantee
drift and obscure which agent runs in production, so the duplicate is removed and the single
source of truth is made explicit.

## What Changes

- **Remove `nhisokf/`** entirely (reimplemented agent, stale bundle copy, second agentcore
  scaffold, and its generated CDK/cache/venv artifacts). Drop the now-moot `nhisokf/**`
  `.gitignore` rules.
- **`deploy/` is the single deploy tree.** No code change needed — it already targets
  `src/nhis_okf/agentcore_app.py` and the committed `.okf/` bundle. Document it as canonical.

## Impact

- Affected specs: `okf-compiler` (MODIFIED: one deploy tree, one agent, one bundle).
- Affected code: delete `nhisokf/`; `.gitignore`. No change to `src/nhis_okf`, the bundle, or
  any behavior.
- Follow-on (separate, gated): porting query-time compute (pandas/pyarrow + curated parquet)
  into the deployed runtime for Path B needs a **container** build under `deploy/agentcore/`
  (the CodeZip limit is a documented 250 MB compressed / 750 MB uncompressed; container is 2 GB).
  The `deploy/` layout is switch-safe — `deploy/infra` + `deploy/lambda` only consume a
  `runtimeArn`, so CodeZip→container touches only `deploy/agentcore/`.
