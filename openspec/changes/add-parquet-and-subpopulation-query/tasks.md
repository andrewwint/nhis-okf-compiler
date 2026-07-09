# Tasks: parquet storage layer + survey-weighted subpopulation query

Keeps the non-negotiables: verification executes (never lints), survey weights are
mandatory, and the safety scope holds — the query surface returns aggregates only, never
raw individual records.

## 1. Parquet storage layer
- [x] 1.1 Add `pyarrow` to `pyproject.toml` dependencies
- [x] 1.2 A parquet materialization step (build `.parquet` next to each `data/*.csv`), wired into `nhis fetch` and/or a `nhis build` subcommand; idempotent
- [x] 1.3 `analysis.load_microdata` and `trends.year_csv` prefer the parquet twin when present, fall back to CSV; column projection intersects requested columns with those available (parquet must not throw on a missing column the CSV path silently skipped)
- [x] 1.4 Tests: parquet and CSV paths produce identical prevalence/mean estimates; missing-column projection is handled

## 2. Distributional statistics (umbrella change §2 — implemented here)
- [x] 2.1 `analysis.weighted_mean` and `analysis.weighted_quantile` (survey-weighted; non-substantive codes dropped via the registry `valid_codes`)
- [x] 2.2 Extend the `Concept` model + `verify.py` to check mean/quantile claims (a `kind` discriminator), comparing to the registry-correct computation with tolerance in the variable's units
- [x] 2.3 Wire `DIBAGETC_A` as a verified weighted-mean concept (age at diagnosis, universe `DIBEV_A == 1`) plus a seeded wrong-mean defect; `nhis verify` catches the defect, `nhis compile` quarantines it
- [x] 2.4 Tests: age-at-diagnosis weighted mean verified; a wrong mean (unweighted or 96–99 not dropped) is caught

## 3. Survey-weighted subpopulation query
- [x] 3.1 `analysis.subpopulation_stat` (or equivalent): arbitrary universe expression + statistic kind (prevalence/mean/quantile) → survey-weighted aggregate + design-based CI; returns a result object, never a row set
- [x] 3.2 `nhis analyze` CLI path exposing it; grounded-or-refuse — answers only for a variable backed by a verified concept, refuses otherwise
- [x] 3.3 Tests: subpopulation weighted estimate returns a CI and never emits raw rows; an unverified variable is refused; the universe-expression trust-boundary note is preserved

## 4. Closeout
- [x] 4.1 `./.venv/bin/pytest -q` green; `nhis verify` + `nhis compile` green (seeded defects quarantined, no real regressions)
- [x] 4.2 Update umbrella change `build-end-to-end-nhis-okf/tasks.md` §2 checkboxes to reflect completion
- [x] 4.3 `openspec validate add-parquet-and-subpopulation-query --strict` passes
