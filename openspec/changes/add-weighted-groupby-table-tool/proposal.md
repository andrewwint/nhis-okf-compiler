# Change: Deterministic weighted groupby table tool

## Why

The chat can answer a single ad-hoc weighted subgroup (`analyze_subpopulation`), but a
"tabular" answer — e.g. insulin use *by sex*, mean weight *by BMI category* — currently
requires the LLM to call the tool once per group and assemble the table itself. That makes
the *table assembly* LLM-driven, which is weaker than the deterministic cells. A single
deterministic groupby tool returns the whole table (one row per group, each cell weighted
with its design-based CI) in one call — so the table, not just the cells, is deterministic.

## What Changes

- **`analysis.groupby_table(variable, groupby, stat, ...)`** — for each substantive value of
  a grouping column, compute the survey-weighted aggregate + design-based CI, returning a
  table (a list of per-group aggregates). Drops non-substantive group codes, caps the number
  of groups, weights every cell mandatorily. Aggregate-only — cells are aggregates, never
  rows.
- **CLI (internal):** `nhis analyze --groupby <COL>` prints the weighted table.
- **Agent tool (local):** `groupby_table` registered on the chat agent alongside
  `search_verified_okf` and `analyze_subpopulation`, grounded-or-refuse (measured variable
  verified), so the local chat answers "by-group" questions as a single deterministic table.

## Impact

- Affected specs: `okf-compiler` (ADDED: deterministic weighted groupby table).
- Affected code: `analysis.py` (groupby_table + a TableResult), `cli.py` (`--groupby`),
  `chat.py` (agent tool + prompt), `tests/`, `docs/SAMPLE.md`.
- Relationship to deploy: this is the compute that the Path B deploy will port into the
  AgentCore runtime; the deploy port (deps + parquet packaging) is a **separate** change.
- Out of scope (deferred): the AgentCore runtime port/deploy; raw-row tables (stay
  researcher CLI); cross-tabs on two grouping variables (single groupby first).
