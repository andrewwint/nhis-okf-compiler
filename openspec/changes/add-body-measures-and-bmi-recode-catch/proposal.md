# Change: Body-measure concepts + the BMI cross-year recode catch

## Why

The diabetes/hypertension slice proved prevalence and (now) weighted-mean verification.
Body-measure variables (weight, height) exercise the mean/quantile path on whole-sample
continuous data, and the 2018→2023 body-measure rename exposes a **second, harder class of
redesign defect** the current verifier cannot catch: not a renamed-to-absent variable, but
a **silent recode**. Both years carry a "BMI" column, so nothing is absent and the markdown
is clean — but 2018 `BMI` is a continuous value stored ×100 (integer 2814 = BMI 28.1) while
2023 `BMICAT_A` is a 1–4 category. A naive mean-BMI trend joins them and produces a
confidently-wrong series (~2814 → ~2.5) that a rename-gap check passes. Catching that
advances the "verification executes, not lints" thesis into a new failure mode.

## What Changes

- **Body-measure concepts (2023).** Add `WEIGHTLBTC_A` (weight, lbs) and `HEIGHTTC_A`
  (height, in) as verified weighted-mean concepts over the whole adult sample, each with a
  seeded defect that retains the non-substantive top-codes (996–999 / 96–99), which badly
  inflates the mean. Add `WEIGHTLBTC_A`, `HEIGHTTC_A`, `BMICAT_A`, `SEX_A` to the loaded
  column slice so the query surface can reference them.
- **Cross-year encoding-compatibility check (the BMI recode catch).** Add a guard to trend
  verification that compares the resolved per-year variables' value domains and fails a
  join across incompatible encodings (categorical vs continuous, or non-overlapping
  domains) with a diagnosis — **before** any value comparison. Seed a `TREND_bmi__naive`
  concept that joins 2018 `BMI` (continuous ×100) to 2023 `BMICAT_A` (1–4 category); it is
  caught and quarantined. The correct outcome for this pair is "not comparable" — there is
  no valid mean-BMI trend to publish.
- **Sex-stratified subpopulation queries (if #1 and #2 land).** Demonstrate that
  `nhis analyze --universe "SEX_A == 1"` gives subgroup weighted estimates with **no engine
  change** — the existing query surface generalizes once `SEX_A` is in the slice.

## Impact

- Affected specs: `okf-compiler` (ADDED: whole-sample continuous concepts; ADDED: cross-year
  encoding-compatibility check).
- Affected code: `registry.py` (body-measure variables + a `bmi` cross-year entry),
  `concepts/` (WEIGHTLBTC_A, HEIGHTTC_A + seeded defects; TREND_bmi__naive),
  `trends.py` (encoding-compatibility guard), `cli.py` (SLICE_COLUMNS), `tests/`.
- Out of scope (deferred): a full continuous cross-year mean-trend engine (BMI has no valid
  continuous counterpart in 2023, so the catch is refusal, not computation); parquet
  slimming (rejected — the twin must keep all columns for arbitrary-universe queries and
  raw non-substantive codes for the seeded defects); AWS deploy.
