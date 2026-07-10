# Tasks: deterministic query-time subpopulation tool for the chat agent

The chat (AgentCore) is the only end-user surface. The new tool is deterministic,
registry-correct, weighted, grounded-or-refuse, and aggregate-only. Raw rows
(`parquet_query` / `nhis rows`) stay unreachable from the agent.

## 1. The agent tool
- [x] 1.1 In `chat.py`, add an `analyze_subpopulation(variable, universe, stat, q?)` tool wrapping `analysis.subpopulation_stat`: returns the survey-weighted estimate + design-based CI as text for the agent. Grounded-or-refuse — only variables backed by a verified concept in the compiled bundle (reuse the same verified-variable allow-list the CLI uses); refuse otherwise. Aggregate-only; never returns rows.
- [x] 1.2 Register the tool on the Strands agent alongside `search_verified_okf`; update `OKF_ANALYST_PROMPT` so the agent uses retrieval for a precomputed concept and `analyze_subpopulation` for an ad-hoc weighted subgroup, always states the universe/weight basis, and refuses rather than guesses.
- [x] 1.3 Empty-universe / unverified-variable inputs surface as a refusal through the tool, not a fabricated number (reuse subpopulation_stat's guards).

## 2. Boundary preserved
- [x] 2.1 Confirm the agent still cannot reach the raw-row tool: `chat.py`/`agentcore_app.py` do not import `parquet_query` (existing boundary test still passes).
- [x] 2.2 The new tool returns only a scalar aggregate + CI (no DataFrame/rows).

## 3. Hermetic tests (no network)
- [x] 3.1 With a stub model, assert the agent invokes `analyze_subpopulation` for a subgroup question and surfaces the weighted figure + CI; assert an unverified variable is refused.
- [x] 3.2 The raw-row boundary test still passes; `nhis analyze`/`nhis rows` CLI unchanged.

## 4. Docs: reflect the two-tool RAG
- [x] 4.1 Update `README.md` (the "How it works" diagram + prose) to show the agent's two deterministic tools — retrieval over the verified bundle (grounded-at-compile-time) and `analyze_subpopulation` (execution-grounded-at-query-time) — and that raw rows are never an agent tool.
- [x] 4.2 Update `docs/SAMPLE.md` so the chat is the end-user surface: show the chat answering a precomputed-concept question AND an ad-hoc subgroup question (real `nhis query` output), with the CLI (`nhis analyze`/`nhis rows`) framed as internal/researcher, not the end-user surface.

## 5. Closeout
- [x] 5.1 `./.venv/bin/pytest -q` green; `nhis verify`/`trends`/`compile`/`conformance` green (unchanged); `nhis query "…"` demonstrably answers an ad-hoc subgroup question with a weighted figure + CI, and refuses an unverified one.
- [x] 5.2 `openspec validate add-subpopulation-agent-tool --strict` passes.
- [x] 5.3 Update tasks.md checkboxes.
