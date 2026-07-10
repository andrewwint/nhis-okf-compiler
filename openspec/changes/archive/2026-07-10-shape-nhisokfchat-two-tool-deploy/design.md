# Design: shape `nhisokfchat` to the article's two-tool agent

## Context

The deploy is the companion to a jr/mid how-to. It must expose the article's **two tools**
(retrieve + compute), runnably, and the compute tool must be the **hardened, aggregate-only**
one — not the article's raw `df.query(universe)` (an injection sink) and not a raw-row tool.
Earlier this change trimmed the deploy to retrieval-only by physical absence; that interim state
is now superseded by the two-tool target the article teaches.

## The two tools (the deployed surface)

```
main.py  →  BedrockAgentCoreApp  →  chat.answer  →  Strands Agent with:
    1. search_verified_okf(query)            retrieval over the verified OKF bundle (Phase 1)
    2. analyze_subpopulation(variable,        survey-weighted % + design CI for an ad-hoc
       universe)                              subgroup (Phase 2), verified vars only, aggregate
```

`analyze_subpopulation` is the LAB's hardened tool, ported verbatim in spirit:
- **Verified-variables gate** — the variable must be backed by a compiled concept, else REFUSED.
- **Universe allow-list gate** — the agent's `universe` string passes `analysis.validate_universe`
  (`COLUMN <op> NUMBER` joined by `& | ( )` over real columns) before `df.eval`. This is the
  `injection-sink@universe-eval` mitigation; the article's `df.query(universe)` is replaced by it.
- **Aggregate only** — returns a percentage + Taylor-linearization CI, never rows.

## What ships (and what does not)

Keep the reader-facing wins already landed: build-only modules gone, `ANTHROPIC_API_KEY` dropped
(Bedrock-only), flattened `main.py`.

Re-vendor for tool #2:
- `analysis.py` (from the LAB `src/nhis_okf/` — the hardened version with `validate_universe`,
  `subpopulation_stat`, `design_based_ci`, `load_microdata`) and `registry.py` (its dependency).
- `pandas` (+ `pyarrow` for parquet) in `pyproject.toml`. `numpy` already arrives via sklearn.
- A **slim NHIS 2023 parquet** shipped beside the code, carrying only the columns the verified
  variables and the survey design (`WTFA_A`, `PSTRAT`, `PPSU`, `SEX_A`, the verified vars) need —
  not the full microdata. Path resolves via config with a shipped-bundle fallback, mirroring
  `okf_dir()`.

Still **never** ships: `parquet_query.py` (the raw-row tool) and any row-returning agent tool.
Raw-row inspection stays a local-only capability.

## Security — the seam returns to the deploy, deliberately

The interim trim removed `df.eval` from the artifact by physical absence. Re-adding
`analyze_subpopulation` re-introduces the `injection-sink@universe-eval` seam into the deployed
artifact. This is recorded (`record_seam.py` → `triaged_seams.jsonl`) so the completeness gate
arms, and verification includes an **independent `security-review`** deriving the seam's
invariants and adversarially attacking `validate_universe`, plus a written disposition. The
functional gate (both tools answer) is necessary but not sufficient.

## Verification — execute both tools, attack the seam

- Retrieval: verified insulin question → 31.96% `[DIBINS_A]`.
- Compute: "insulin use among women with diabetes" → `analyze_subpopulation` over
  `DIBEV_A == 1 & SEX_A == 2`, weighted, ~31.9% with a design CI; an unverified variable → REFUSED.
- Injection: a crafted universe (attribute/call/import/bare name) → REFUSED, never evaluated.
- Grounded-or-refuse and the two-tool `OKF_ANALYST_PROMPT` intact.

## Alternatives considered

- **Keep one tool, show compute as the LAB's job in the article.** Rejected by the article-parity
  goal: the reader must be able to run both tools in the one repo they cloned.
- **Compute via AgentCore Code Interpreter + S3 (pandas-free CodeZip).** The faithful production
  path, but S3 + IAM + Code-Interpreter wiring is too much apparatus for the article's audience.
  Deferred; the in-CodeZip pandas path is the approachable version.
- **Ship the article's `df.query` as-is.** Rejected: it is a live injection sink and teaches jr
  engineers an RCE pattern. The hardened `analyze_subpopulation` is the only acceptable tool #2.
