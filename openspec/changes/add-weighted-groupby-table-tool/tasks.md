# Tasks: deterministic weighted groupby table tool

Aggregate-only (cells are weighted aggregates + CI, never rows); weights mandatory;
grounded-or-refuse on the measured variable. No raw-row path.

## 1. The groupby compute
- [x] 1.1 `analysis.groupby_table(variable, groupby, *, stat="prevalence", q=0.5, extra_universe=None)`: for each SUBSTANTIVE value of `groupby` (drop non-substantive codes, e.g. SEX_A 7/9), compute the survey-weighted aggregate + design-based CI over that group (reuse subpopulation_stat / the design-CI machinery), returning a small `TableResult` (ordered list of per-group cells: group value, estimate, CI, SE, n, weighted denom). Cap the number of groups (e.g. <= 20; error if exceeded). Optional `extra_universe` to combine a filter with the grouping.
- [x] 1.2 A readable `TableResult.summary()` rendering the table (group | estimate | 95% CI | n), plus the survey-weighted basis line.
- [x] 1.3 Tests: groupby prevalence and mean produce one weighted cell per group with a CI; non-substantive group codes dropped; the group cap is enforced; cells match a direct per-group `subpopulation_stat`.

## 2. CLI (internal/researcher)
- [x] 2.1 `nhis analyze --groupby <COL>` prints the weighted table (aggregate cells only, no rows). Keep existing `nhis analyze` behavior when `--groupby` is absent.
- [x] 2.2 Test: `--groupby SEX_A` returns a 2-row weighted table with CIs.

## 3. Agent tool (local chat)
- [x] 3.1 `groupby_table` Strands tool in `chat.py`, registered alongside `search_verified_okf` and `analyze_subpopulation`; grounded-or-refuse (measured variable must be verified; refuse otherwise, never fabricate). Aggregate-only. Update the prompt so the agent uses it for a "by <group>" question.
- [x] 3.2 Agent boundary preserved: chat.py still does not import the raw-row tool; the new tool returns only aggregate table text.
- [x] 3.3 Hermetic test (stub model): the agent invokes `groupby_table` for a by-group question and surfaces the weighted table; an unverified measured variable is refused.

## 4. Docs
- [x] 4.1 Add a real `nhis analyze --groupby` example (and a chat by-group example) to `docs/SAMPLE.md`, framed as an aggregate table.

## 5. Closeout
- [x] 5.1 `./.venv/bin/pytest -q` green; `nhis verify`/`trends`/`compile`/`conformance` green and unchanged.
- [x] 5.2 `openspec validate add-weighted-groupby-table-tool --strict` passes.
- [x] 5.3 Update tasks.md checkboxes.
