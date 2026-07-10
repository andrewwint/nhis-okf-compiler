## Context

The lean slice loads a 29 MB CSV per call and answers only pre-authored concept
statistics. This change adds a faster columnar store and an ad-hoc, still-survey-correct
query surface, without changing the verification spine or the safety scope.

## Goals / Non-Goals

- Goals: parquet twin with identical estimates and CSV fallback; weighted mean/quantile as
  first-class query kinds; an arbitrary-universe query that always terminates in a weighted
  aggregate + design-based CI.
- Non-Goals: raw individual-record access, a web/API surface, multi-dataset abstraction,
  replacing CSV as the fetched source of truth.

## Decisions

- **CSV stays the source of truth; parquet is a derived cache.** CDC ships CSV and
  `nhis fetch` depends on it. Parquet is materialized alongside and preferred on load; delete
  it and the CSV path still works. This mirrors the existing `index ⊆ verified OKF` "derived,
  never coupled" stance.
- **Parquet loader intersects requested columns with available ones.** The CSV path uses a
  `usecols` lambda that silently ignores columns absent from a given year's file;
  `read_parquet(columns=...)` raises on a missing column. To preserve behavior, project only
  the intersection. This matters for the multi-year files, whose column sets differ.
- **Row filtering is the *means*; a weighted aggregate is the *output*.** The query surface
  reuses `analysis._mask` / `compute_prevalence`, which already filter to an arbitrary
  universe, and returns a `PrevalenceResult` / mean / quantile plus a `DesignCI`. There is no
  code path that returns individual rows — this is the safety-scope invariant, verified by an
  independent review lens.
- **Grounded-or-refuse extends to ad-hoc queries.** A query is answered only for a variable
  backed by a verified concept in the compiled bundle; an unverified variable is refused, so
  the ad-hoc surface cannot ship a number the verification gate never saw.
- **Extend the one engine; do not fork it.** Mean/quantile follow the same explicit-knobs
  pattern as prevalence so a flawed method stays expressible and therefore catchable.

## Risks / Trade-offs

- Parquet/CSV drift (a stale twin) → loaders key off the CSV as source of truth and the
  build step is idempotent; tests assert estimate equality across both paths.
- `df.eval` on a CLI-supplied universe expression is a code-injection vector if this ever
  gains a web surface or untrusted input → preserve the existing trust-boundary note in
  `_mask`; the tool runs locally against public data authored/queried by the same user who
  already holds the CSV.

## Migration Plan

Additive. No existing concept, spec, or command changes behavior; parquet is preferred only
when present, else the CSV path is unchanged.

## Open Questions

- Whether parquet materialization lives in `nhis fetch` (automatic) or a separate
  `nhis build` (explicit) — leaning automatic-on-fetch with a standalone builder available.
