## Context

Body measures extend the weighted-mean path to whole-sample continuous variables, and the
2018→2023 body-measure rename surfaces a defect class the current trend verifier misses:
a silent recode, not a rename-to-absent. Both years have a "BMI" column, so the existing
rename-gap check (variable-absent) passes it.

## Goals / Non-Goals

- Goals: verified weighted-mean concepts for weight and height; a cross-year guard that
  catches an incompatible-encoding join (BMI continuous ×100 vs BMICAT_A category); prove
  subgroup queries generalize with no engine change.
- Non-Goals: a full continuous cross-year mean-trend engine; parquet slimming/cleaning;
  publishing a BMI trend (there is no valid one — 2023 dropped continuous BMI).

## Decisions

- **The BMI catch is a refusal, not a computation.** 2018 `BMI` is continuous (×100 implied
  decimal, ~11–100); 2023 `BMICAT_A` is a 1–4 category. There is no valid mean-BMI trend to
  publish across the redesign, so the correct verifier behavior is to **detect the
  incompatible encoding and fail the join** — not to compute a "correct" trend. This keeps
  the change bounded: we add a guard, not a continuous-trend engine.
- **Guard runs before the value check.** The existing `verify_trend` value path uses
  `compute_prevalence` (prevalence trends). A mean-BMI join has no affirmative-codes to
  prevalence-compute, so the encoding-compatibility guard must run first and short-circuit
  with its diagnosis, leaving the prevalence path untouched for the diabetes trend.
- **Compatibility is judged empirically.** Read a sample of each year's resolved column and
  compare substantive value domains (min/max/cardinality). Categorical-vs-continuous or
  non-overlapping ranges ⇒ incompatible. Consistent with the skill rule to confirm the data
  empirically rather than trust names.
- **Keep the parquet twin full and raw.** Do not column-project or value-clean it: the
  seeded defects depend on raw non-substantive codes (996–999) being present, and the
  arbitrary-universe query can reference any column (e.g. `SEX_A`); a slim twin would
  silently drop a referenced column and never fall back to CSV. Columnar compression already
  provides the size win (29 MB CSV → ~5 MB parquet).
- **Extend the one engine; do not fork it.** Body-measure means reuse `weighted_mean` and
  the design-based mean CI unchanged; only the registry and concept files grow.

## Risks / Trade-offs

- A too-loose compatibility check could pass a real recode or flag a benign one → base it on
  clear signals (categorical small-integer domain vs wide continuous range; disjoint
  ranges) and cover both the BMI catch and the still-valid diabetes trend in tests.
- Whole-sample universe assumption for body measures → verified empirically in task 1.1
  (n≈29,522 = all adults) before trusting it.

## Migration Plan

Additive. New variables, concepts, and a new trend guard; the prevalence/CI/rename paths and
all existing concepts are unchanged.

## Open Questions

- Whether to also add a 2023 `BMICAT_A` distribution concept (category shares) — deferred;
  the batch's point is the recode catch, not BMI reporting.
