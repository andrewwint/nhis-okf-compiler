# Tasks: body-measure concepts + BMI cross-year recode catch

Non-negotiables hold: verification executes (never lints), survey weights mandatory,
aggregate-only safety scope. The parquet twin keeps all columns and raw values (do not slim
or clean it — the seeded defects need raw non-substantive codes and arbitrary-universe
queries need every column).

## 1. Body-measure concepts (2023, whole-sample weighted means)
- [x] 1.1 Registry entries: `WEIGHTLBTC_A` (weight lbs; valid 100–299; drop 996–999; whole-sample universe; weight WTFA_A) and `HEIGHTTC_A` (height in; valid 59–76; drop 96–99; whole-sample; WTFA_A) — confirm universes empirically (n≈29,522 = all adults, no skip-pattern)
- [x] 1.2 Concepts `concepts/WEIGHTLBTC_A.yaml` + `concepts/HEIGHTTC_A.yaml` as verified weighted-mean claims (compute the true values against the data), each with a seeded defect that retains the non-substantive top-codes (e.g. `WEIGHTLBTC_A__rawcodes` widening valid_codes to include 996–999) → inflated mean caught by execution
- [x] 1.3 Add `WEIGHTLBTC_A`, `HEIGHTTC_A`, `BMICAT_A`, `SEX_A` to `SLICE_COLUMNS` in cli.py
- [x] 1.4 `nhis verify` catches the seeded defects (FAIL while lint passes); `nhis compile` writes the sound concepts and quarantines the defects; `nhis conformance` PASS
- [x] 1.5 Tests: each body-measure mean verified; each seeded defect caught

## 2. Cross-year encoding-compatibility check (the BMI recode catch)
- [x] 2.1 Registry `CROSS_YEAR["bmi"]` mapping 2018 `BMI` (WTFA_SA) → 2023 `BMICAT_A` (WTFA_A), carrying enough to describe each year's encoding (continuous vs categorical / substantive domain)
- [x] 2.2 `trends.py`: an encoding-compatibility guard that compares the resolved per-year variables' empirical value domains and, on incompatible encodings (categorical vs continuous, or non-overlapping substantive ranges), emits a diagnosis and FAILs — running BEFORE the prevalence value-check so it short-circuits (no continuous-trend engine is built)
- [x] 2.3 Seed `concepts/trends/TREND_bmi__naive.yaml` claiming a mean-BMI trend joining `BMI`→`BMICAT_A`; `nhis trends` catches it (lint passes, execution fails) and `nhis compile` quarantines it
- [x] 2.4 Tests: the BMI recode join is caught with a scale/units-mismatch diagnosis; the existing DIBEV1→DIBEV_A rename catch and the valid diabetes trend still behave unchanged

## 3. Sex-stratified subpopulation queries (only if 1 and 2 pass)
- [x] 3.1 Confirm `nhis analyze --variable WEIGHTLBTC_A --universe "SEX_A == 1" --stat mean` and `SEX_A == 2` give distinct subgroup weighted estimates + CIs, with NO engine change
- [x] 3.2 Test: a sex-stratified subpopulation query returns an aggregate (no raw rows); add a short sample to docs/SAMPLE.md

## 4. Closeout
- [x] 4.1 `./.venv/bin/pytest -q` green; `nhis verify` + `nhis trends` + `nhis compile` + `nhis conformance` green (defects quarantined, no real regressions)
- [x] 4.2 `openspec validate add-body-measures-and-bmi-recode-catch --strict` passes
- [x] 4.3 Update tasks.md checkboxes to reflect what actually landed
