# Change: Shape `nhisokfchat` to the article — a two-tool, injection-hardened deploy

## Why

The deployable repo `../nhisokfchat` is the companion to a published how-to whose audience is
**junior-to-mid engineers who read the article and then clone and run the repo**. For that
reader the governing contract is simple: **the code in the article and the code in the repo
must be the same code, and both must actually run.** The reference article is
`/Users/andrewwint/Documents/PROJECTS/PRODUCTS/discipline/docs/articles/aws-agentcore-okf-how-to.md`.

The article teaches **two tools** — a retrieval tool over the verified OKF bundle (Phase 1) and
a query-time survey-weighted computation tool (Phase 2) — because two tools tell the real
grounded-agent story (retrieve a precomputed concept *and* compute an ad-hoc subgroup). The repo
must expose those same two tools, runnably.

Two gaps to close so article == repo:
- The repo currently ships **one** tool (retrieval only), after an earlier physical-retrieval-only
  trim. It must regain the second (compute) tool to match the article.
- The article's Phase 2 snippet is **not safe to ship as written**: it calls
  `df.query(universe_expression)` on unvalidated agent text (a code-injection sink) and uses a
  fictional `agentcore`/`@app.tool` API. A jr engineer copying it gets an `ImportError` and an RCE
  pattern. The repo's second tool must be the **hardened, aggregate-only** computation, and the
  article snippet is corrected to match it (article track).

## What Changes

Keep what already landed and reads well for a reader: the build-only-module trim, the
`ANTHROPIC_API_KEY` drop (Bedrock-only), and the flattened real `main.py` entrypoint.

Add the second tool, done safely:
- **Re-vendor the hardened compute engine** the deploy needs for tool #2: `analysis.py`
  (carrying `validate_universe`, `subpopulation_stat`, `design_based_ci`) and its `registry.py`
  dependency, plus `pandas` in the runtime deps and a **slim NHIS 2023 parquet** (only the columns
  the verified variables + survey design need) shipped beside the code.
- **Tool #2 = `analyze_subpopulation`** — a deterministic, survey-weighted aggregate (percentage +
  design-based CI) for an ad-hoc subgroup, restricted to **verified variables only**, returning
  **aggregate cells only (never raw rows)**, and refusing rather than guessing. Its
  agent-supplied `universe` passes the **allow-list validator** (`COLUMN <op> NUMBER` joined by
  `& | ( )` over known columns) before any `df.eval` — the article's `df.query` becomes this.
- **The agent now advertises two tools** in `OKF_ANALYST_PROMPT` and `_as_tools()`:
  `search_verified_okf` (precomputed concept) and `analyze_subpopulation` (ad-hoc weighted
  subgroup). Raw rows remain a **local-only** capability that never ships to the deploy.
- **Correct the article** to the real `bedrock_agentcore` API + the hardened two-tool code
  (tracked with this change; the article file lives in the discipline repo).

## Impact

- Affected: `../nhisokfchat` (re-adds `analysis.py`/`registry.py`, `pandas` dep, a slim parquet,
  tool #2 in `chat.py`); the draft article (API + Phase-2 correction).
- Spec: `okf-compiler` — the deployed agent's tool surface is **two aggregate tools**; the
  `injection-sink@universe-eval` seam is present in the deploy and gated by the allow-list.
- **Security:** this deliberately **re-introduces the `injection-sink@universe-eval` seam** into
  the deployed artifact (the earlier trim had removed it by physical absence). Verification MUST
  include an independent `security-review` on that seam and a recorded disposition — not just the
  functional gate.
- Supersedes the interim "physical retrieval-only" framing: the deploy is now **aggregate-only,
  two-tool, injection-gated** (no raw rows, no `df.query`), not zero-compute.
