---
type: variable_definition
title: "Ever told you had high blood pressure"
description: "Weighted prevalence of diagnosed hypertension among U.S. adults, 2023"
resource: "https://www.cdc.gov/nchs/nhis/2023nhis.htm"
tags: [nhis-2023, diabetes, HYPEV_A, prevalence]
timestamp: "2026-06-29T11:45:35Z"
# extension keys (OKF consumers tolerate unknown fields)
id: HYPEV_A
variable: HYPEV_A
question_universe: "All sample adults."
weight: WTFA_A
source: "NHIS 2023 Sample Adult public-use file (adult23.csv)"
statistic: "Weighted prevalence of diagnosed hypertension among U.S. adults, 2023"
value_pct: 32.26
verification:
  verdict: PASS
  method: execution-grounded
  correct_pct: 32.26
  claimed_pct: 32.26
  delta_pp: 0.0
  detail: "32.26% (weighted by WTFA_A; universe: all sample adults; n=29471 unweighted)"
  verified_at: 2026-06-29T11:45:35Z
---

# Ever told you had high blood pressure

HYPEV_A records whether a sample adult was ever told by a health professional that they
had high blood pressure (hypertension). "Diagnosed hypertension" is HYPEV_A == 1. The
population estimate must be survey-weighted (WTFA_A); the unweighted sample share does not
estimate the U.S. adult population.

## Verified statistic

**Weighted prevalence of diagnosed hypertension among U.S. adults, 2023: 32.26%**

- Basis: 32.26% (weighted by WTFA_A; universe: all sample adults; n=29471 unweighted)
- Verification: executed against NHIS 2023 Sample Adult public-use file (adult23.csv); verdict **PASS**.

## Related
- [HYPMED_A](./HYPMED_A.md)
