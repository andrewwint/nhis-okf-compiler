# Change: Parquet storage layer + survey-weighted subpopulation query

## Why

Today the engine loads a 29 MB CSV and re-parses it on every call, and querying is
effectively column-level: you can ask a pre-authored concept's headline statistic, but you
cannot pose an ad-hoc "for *this* subpopulation, what is the weighted estimate?" question.
Analysts need to slice across rows (define an arbitrary universe) and still get a
survey-correct number — without ever exposing individual records, which would violate the
aggregate-only safety scope and invite the exact unweighted-count defect this project
exists to catch.

## What Changes

- **Parquet columnar storage.** Keep the CDC-shipped CSV as the fetched source of truth, but
  materialize a `.parquet` twin next to each `data/*.csv`. Loaders (`analysis.load_microdata`,
  `trends.year_csv`) prefer the parquet when present and fall back to CSV, so column
  projection is pushed down to the file and repeat loads are typed and fast. Estimates MUST
  be identical across the two paths.
- **Survey-weighted subpopulation query.** A function + `nhis analyze` CLI path that takes an
  arbitrary universe expression (pandas row filtering across rows) plus a statistic kind
  (prevalence / mean / quantile) and returns **only** a survey-weighted aggregate with its
  design-based confidence interval. It is grounded-or-refuse: it answers only for a variable
  backed by a verified concept in the bundle, and it NEVER returns raw individual rows.

## Impact

- Affected specs: `okf-compiler` (ADDED: parquet storage layer; ADDED: subpopulation query).
- Affected code: `analysis.py` (parquet-aware loader, `weighted_mean`/`weighted_quantile`,
  subpopulation aggregate), `trends.py` (parquet-preferring per-year load), `cli.py`
  (`nhis analyze`, parquet build in `fetch`), `pyproject.toml` (`pyarrow`), `tests/`.
- Depends on the umbrella change's "Distributional and continuous statistics" requirement
  (weighted mean/quantile), implemented in the same batch; this change consumes it for the
  mean/quantile query kinds.
- Out of scope (deferred): DIBTYPE_A / DIBA1CLAST_A coverage; AWS deploy; any raw
  individual-level record access or a web surface.
