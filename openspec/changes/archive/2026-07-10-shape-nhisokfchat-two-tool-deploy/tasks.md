# Tasks: shape `nhisokfchat` to the article's two-tool agent

Align the deployable repo `../nhisokfchat` to the article
(`.../discipline/docs/articles/aws-agentcore-okf-how-to.md`): two tools (retrieval + hardened
aggregate compute), runnable, injection-gated. Verification EXECUTES both tools and attacks the
seam. Merging/pushing the sibling repo is gated on approval.

## 1. Already landed (reader-simplification base) — verified
- [x] 1.1 Trim build-only modules from the deploy vendor (`compiler, verify, trends, concepts,
  cli, __main__`). These never belong in the deploy.
- [x] 1.2 Drop local `ANTHROPIC_API_KEY` support — Bedrock-only (`chat.build_chat_agent`, the
  `config` anthropic helpers, dead `_load_dotenv`, the `answer()` generative-default term).
- [x] 1.3 Flatten the entrypoint into one real `main.py` (`BedrockAgentCoreApp` + `_parse_question`
  + `@app.entrypoint invoke` + `@app.ping`); delete `agentcore_app.py`; drop the env-setdefaults
  (bundle resolves via `config.okf_dir()` fallback). Execute-verified: import-clean, `main.app` is
  `BedrockAgentCoreApp`, `invoke` returns the structured grounded answer.

## 2. Re-vendor the hardened compute engine (for tool #2)
- [ ] 2.1 Copy the LAB `src/nhis_okf/analysis.py` (the hardened version: `validate_universe`,
  `_UniverseParser`, `subpopulation_stat`, `design_based_ci`, `load_microdata`/`load_table`) and
  `src/nhis_okf/registry.py` (its dependency) into `../nhisokfchat/app/nhisokfchat/nhis_okf/`.
  Do NOT copy `parquet_query.py` (the raw-row tool) — rows never ship.
- [ ] 2.2 Add `pandas` (+ `pyarrow`) to `../nhisokfchat/app/nhisokfchat/pyproject.toml`. Keep the
  deps minimal.
- [ ] 2.3 Ship a **slim** NHIS 2023 parquet beside the code, carrying only the columns the verified
  variables + survey design need (`WTFA_A`, `PSTRAT`, `PPSU`, `SEX_A`, `DIBEV_A`, `DIBINS_A`,
  `PREDIB_A`, and the other verified vars) — not the full microdata. Resolve its path via config
  with a shipped-bundle fallback (mirror `okf_dir()`); set the env/default so `analysis` finds it
  in the deployed layout.

## 3. Tool #2 — the hardened aggregate compute
- [ ] 3.1 In the deploy `chat.py`, add `analyze_subpopulation(variable, universe)` as a Strands
  tool: verified-variable gate (REFUSE unverified), `analysis.validate_universe` on the
  agent-supplied `universe` BEFORE `df.eval`, survey-weighted percentage + design-based CI,
  **aggregate only** (never rows). Port `_validate_agent_universe`/`_agent_allowed_columns` from
  the LAB `chat.py`.
- [ ] 3.2 `_as_tools()` returns BOTH `[search_verified_okf, analyze_subpopulation]` (still no row
  tool). Update `OKF_ANALYST_PROMPT` to describe the two tools and when to use each (precomputed
  concept vs ad-hoc weighted subgroup), keeping grounded-or-refuse and the safety framing.

## 4. Execute-verify the two-tool deploy (functional gate)
- [ ] 4.1 Fresh interpreter: `import main` clean; `_as_tools()` → `['search_verified_okf',
  'analyze_subpopulation']`; `parquet_query` still unimportable (no rows).
- [ ] 4.2 Retrieval: verified insulin question → 31.96% `[DIBINS_A]`. Compute:
  `analyze_subpopulation("DIBINS_A", "DIBEV_A == 1 & SEX_A == 2")` → ~31.9% weighted with a design
  CI and an unweighted n; an unverified variable → REFUSED. Paste real output.
- [ ] 4.3 Injection: a crafted `universe` (attribute access, `__import__`, a call, a bare name) →
  REFUSED, never evaluated. Paste the rejection.

## 5. Security — the seam is back in the deploy (the real gate)
- [x] 5.1 Record the `injection-sink@universe-eval` seam (`record_seam.py`) so the completeness
  gate arms. (Done — `triaged_seams.jsonl` carries it.)
- [ ] 5.2 Independent `security-review` lane on the seam: derive its invariants from the deploy's
  `analysis.validate_universe`/`_mask` + `chat._validate_agent_universe`, adversarially attack the
  validator, confirm both agent tools gate before `df.eval` and no row path exists. Verdict +
  attacks in the closeout.
- [ ] 5.3 Write `.agents/runs/<runId>/disposition.json` for the seam from the security verdict.

## 6. Docs / article alignment
- [ ] 6.1 `../nhisokfchat/README.md` + `docs/SAMPLE.md`: describe the **two** tools (retrieval +
  aggregate compute), aggregate-only, injection-gated; fix any stale text still naming removed
  tools (SAMPLE.md currently references `analyze_subpopulation`/`groupby_table` — reconcile to the
  shipped two-tool reality).
- [ ] 6.2 Correct the article (`.../discipline/docs/articles/aws-agentcore-okf-how-to.md`): real
  `bedrock_agentcore` API (not `from agentcore import AgentCoreApp`/`@app.tool`), and Phase 2's
  `df.query(universe)` → the hardened `analyze_subpopulation` (verified-vars + `validate_universe`,
  aggregate). Article code == repo code, both runnable.

## 7. Closeout (gated)
- [ ] 7.1 Independent `code-reviewer` cold-read on the full diff; both lanes' evidence + the seam
  disposition to the merge gate. Merge/push the sibling repo only on explicit approval.
- [ ] 7.2 `openspec validate shape-nhisokfchat-two-tool-deploy --strict` passes.

## Deferred (tracked, not in this change)
- Refresh the stale `app/nhisokfchat/uv.lock`.
- The pure-python retrieval swap (would let a future deploy drop sklearn and make "light/no-pandas"
  literally true — at which point the one-vs-two-tool weight tradeoff is worth revisiting).
- The AgentCore Code Interpreter + S3 compute path (pandas-free CodeZip) as the production variant.
