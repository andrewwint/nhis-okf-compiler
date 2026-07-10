# Tasks: researcher row-level query tool + OKF usage instructions

The verified path stays aggregate-only. The row tool is the ONE surface that returns raw
rows, by design, over de-identified public-use microdata — and it is kept out of the
deployed grounded agent.

## 1. The researcher row tool
- [x] 1.1 `src/nhis_okf/parquet_query.py`: a function returning the selected columns of rows matching an arbitrary universe expression, via the parquet-preferring `analysis.load_table`. Requires an explicit non-empty column list; enforces a row cap (a bounded default limit). Returns/streams rows for display — this tool intentionally does return individual records.
- [x] 1.2 `nhis rows` CLI: `--columns` (required, comma-separated — **a few columns, not all**: enforce a max column count, e.g. ≤ 12, and error if exceeded), `--universe` (optional), `--limit` (default e.g. 20, hard max e.g. 500). Prints a loud caveat header on EVERY call: raw, unweighted, de-identified public-use records; not population estimates; not verified; use `nhis analyze` for weighted figures. Output is table-shaped (rows × the requested few columns), suitable for building a table or grounding a response.
- [x] 1.3 Preserve/extend the `_mask` df.eval trust-boundary note (universe is CLI-supplied, local, trusted).
- [x] 1.4 Tests: `nhis rows` returns the requested columns for a subpopulation; the caveat header is present; the row cap is enforced; an empty/missing `--columns` errors.

## 2. Boundary: keep rows out of the verified product + agent
- [x] 2.1 Confirm `analysis.subpopulation_stat` / `nhis analyze` remain aggregate-only (unchanged).
- [x] 2.2 Test: neither `chat.py` nor `agentcore_app.py` imports `parquet_query` or otherwise reaches the row-returning function (assert on the import graph / source), so the deployed agent cannot emit rows.

## 3. OKF usage instructions
- [x] 3.1 Emit a `references/parquet_query.md` **Reference** concept into the bundle (OKF v0.1 conformant: parseable frontmatter, non-empty `type: Reference`) documenting the tool: purpose, `nhis rows` usage, the raw/unweighted caveat, the column caveats, and how to move from a raw-row inspection to a verified `nhis analyze` aggregate. Frame the bundle as **two deterministic OKF retrieval modes**: (1) fast COLUMN-LEVEL lookup of verified concepts + trends (precomputed weighted aggregates), and (2) deterministic ROW-LEVEL query (`nhis rows`, a few columns) to build a table or ground a response. Source it from `concepts/references/` (or an equivalent) so it is part of the audit trail; keep the rest of the compile unchanged.
- [x] 3.2 Add a `# Reproduce` section to each analytical variable concept in the compiled output, carrying the exact `nhis analyze` (weighted, verified) and `nhis rows` (raw inspection) invocations for that variable/universe.
- [x] 3.3 `nhis conformance` PASS with the new reference concept present.

## 4. Honest safety scope
- [x] 4.1 Update the safety copy (`chat.py` SAFETY / prompt, and CLAUDE.md scope note) to distinguish the verified product (aggregate-only, no individual-level inference) from the local researcher tool (public de-identified microdata inspection). Do not weaken the product's no-individual-inference guarantee.

## 5. Closeout
- [x] 5.1 `./.venv/bin/pytest -q` green; `nhis verify` + `nhis trends` + `nhis compile` + `nhis conformance` green; `nhis rows` and `nhis analyze` both demonstrably behave per their contracts.
- [x] 5.2 `openspec validate add-researcher-row-query-tool --strict` passes.
- [x] 5.3 Update tasks.md checkboxes to reflect what landed.
