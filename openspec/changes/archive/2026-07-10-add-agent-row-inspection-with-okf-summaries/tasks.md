# Tasks: agent row-inspection grounded in OKF column summaries (local, no AWS)

Deliberate approved scope change: the LOCAL agent gains a bounded, caveated raw-row surface.
The DEPLOYED (retrieval-mode) agent stays aggregate-only and pandas-free. No AWS.

## 1. Harden the universe eval (the injection-sink seam)
- [x] 1.1 Add an allow-list validator for universe expressions on the agent path: permit only `COLUMN <==|!=|>=|<=|>|<> NUMBER` tokens joined by `& | ( )`; reject any name/attribute/call/string/other. Reuse or wrap `analysis._mask`; do NOT loosen the existing trust-boundary note. (Added `analysis.validate_universe` + `_UniverseParser`; extended the `_mask` note. Agent tools call it via `chat._validate_agent_universe`.)
- [x] 1.2 Every existing universe must still parse (`DIBEV_A == 1`, `(DIBEV_A == 1) | (PREDIB_A == 1)`, `SEX_A == 2`, `DIBEV_A == 1 & SEX_A == 2`). A crafted injection (attribute access, `__import__`, a function call, a bare name) is rejected with a clear error, not evaluated.
- [x] 1.3 Tests: valid universes pass; a representative set of injection attempts are rejected; the existing tests stay green (the allow-list must not break CLI universes). See `tests/test_universe_allowlist.py`.

## 2. OKF column-summary lookup
- [x] 2.1 A helper that, for a column, returns its verified OKF summary — label, valid codes (with meaning where the registry has it), universe/skip-pattern, from the compiled bundle/registry. A column with no verified concept returns a clear "no OKF summary" note (not a fabrication). (`chat.okf_column_summary`.)
- [x] 2.2 Test: summaries for verified columns (DIBEV_A, DIBINS_A) are correct; SEX_A / an unknown column get the graceful "no OKF summary" note (SEX_A has no verified concept, so the honest note IS the correct answer).

## 3. The agent row tool (default mode only)
- [x] 3.1 In `chat.py`, add a bounded `inspect_rows(columns, universe, limit)` tool wrapping `parquet_query.query_rows` (≤12 columns, hard row cap) that returns: the RAW·UNWEIGHTED·NOT-a-population-estimate banner + the capped rows + the OKF column summary (§2) for each returned column. Universe goes through the §1 allow-list.
- [x] 3.2 Tool-mode gating: register `inspect_rows` ONLY in the default tool set; `NHIS_RUNTIME_TOOLS=retrieval` must NOT include it. `query_rows`/`analysis` are lazy-imported inside the tool so importing chat in retrieval mode stays pandas-free (the existing pandas-free retrieval test still passes; the subprocess test now also asserts `parquet_query` is not imported).
- [x] 3.3 Update `OKF_ANALYST_PROMPT`: use `inspect_rows` for "show me rows / what does this column mean," always print the raw-caveat, prefer the OKF summary for column meaning; keep the aggregate tools + grounded-or-refuse for figures.

## 4. Boundary test flip (the approved change)
- [x] 4.1 The existing "agent cannot reach the raw-row tool" test flips to the new invariant: in RETRIEVAL mode the agent has no row tool and does not import parquet_query/analysis (pandas-free); in DEFAULT mode the row tool is present and its output is capped + caveated. Re-expressed (not deleted) in `tests/test_rows.py` as `test_deployed_retrieval_agent_stays_row_free_and_pandas_free` + `test_default_mode_row_tool_is_present_capped_and_caveated`.

## 5. Docs / framing
- [x] 5.1 README + docs/SAMPLE.md + CLAUDE.md: state the local agent can inspect raw public-use rows (capped, caveated) alongside verified aggregates + OKF column summaries; raw rows are not population estimates. Added a real `nhis query` row-inspection example.

## 6. Closeout (no AWS)
- [x] 6.1 `./.venv/bin/pytest -q` green (128 passed, existing + new). `nhis verify`/`trends`/`compile`/`conformance` unchanged; `.okf/` restored byte-unchanged. Real `nhis query "show me a few rows of insulin use among diabetics and what those columns mean"` returned capped rows + OKF summaries + the caveat (generative, via the local Anthropic key).
- [x] 6.2 `openspec validate add-agent-row-inspection-with-okf-summaries --strict` passes.
- [x] 6.3 Update checkboxes.
