# Build the end-to-end NHIS-OKF product

## Why

The lean diabetes slice (NHIS 2023) proved the thesis end to end: execution-grounded
verification catches a structurally-valid-but-statistically-wrong number (naive insulin
3.66% vs correct 31.96%), quarantines it, and serves only verified figures — confirmed by
an independent cold-read that recomputed the numbers from raw microdata. The slice earns
the expansion to a usable product.

This proposal plans the full end-to-end build on top of that proven core. It is scoped
deliberately: each capability must keep the non-negotiables — verification executes (never
lints), survey weights are mandatory, and the safety scope (public/aggregate, not medical
advice) holds — and must avoid premature abstraction (no portable multi-dataset layer
until reuse earns it).

## What Changes

- **Topic + variable coverage.** Expand beyond the four diabetes variables to the full
  diabetes module (type, A1C testing/recency, pills, age of diagnosis as a distribution),
  then a second condition (hypertension) to show the pattern generalizes within NHIS.
- **Multi-year + the redesign-rename defect.** Add NHIS 2018 (pre-redesign) and a
  post-redesign year, and implement the headline cross-year catch: a longitudinal trend
  that silently joins `DIBEV` → `DIBEV_A` across the 2019 redesign and produces a broken
  series. This is the second marquee defect class named in the product plan.
- **Continuous + distributional statistics.** Extend the analysis engine and verifier
  beyond yes/no prevalence to weighted means and quantiles (e.g. age at diagnosis), with
  the same execution-grounded checking.
- **Design-based variance.** Add Taylor-linearization confidence intervals using
  `PSTRAT`/`PPSU`, so verified figures carry proper survey standard errors, not just point
  estimates.
- **Generative answering, hardened.** Promote the key-gated generative chat from scaffold
  to a first-class, grounded mode with refusal when the verified bundle lacks the answer,
  and a guard that it can only cite verified concepts.
- **Codebook ingestion (discovery).** Parse the NHIS data dictionaries / layout files into
  draft concepts automatically (the "discovery" loop step), so concept authoring scales
  past hand-writing YAML — with verification still gating what enters the bundle.
- **Packaging + eval.** A reproducible `fetch → compile → verify → query` pipeline, plus a
  seeded-defect eval set that measures catch-rate (feeds the review-discipline-eval study
  as a build-then-seed fixture).
- **Safety surface.** Make the not-medical-advice framing first-class in every answer and
  in any UI, and document the aggregate-only data boundary.

## Impact

- Affected specs: `okf-compiler` (extended with multi-year, distributional stats, variance,
  codebook ingestion, hardened generative answering).
- Affected code: `analysis.py` (means/quantiles, design variance), `registry.py` (more
  variables, multi-year universes + rename map), `verify.py` (non-prevalence checks,
  cross-year trend check), `compiler.py` (multi-year bundle + richer log), `chat.py`
  (hardened generative mode), new `ingest_codebook.py`, new `evals/`.
- Out of scope (deferred): a portable multi-dataset (NHANES/BRFSS) abstraction; a hosted
  web UI; any non-public or individual-level data. These wait until the single-dataset
  product earns them.
