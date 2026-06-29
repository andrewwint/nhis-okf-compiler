---
id: DIBAGETC_A
type: variable_definition
label: "Age first told had diabetes (top-coded)"
variable: DIBAGETC_A
question_universe: "Adults ever told they had diabetes (DIBEV_A == 1)."
analytical_universe: "DIBEV_A == 1"
weight: WTFA_A
source: "NHIS 2023 Sample Adult public-use file (adult23.csv)"
verification:
  verdict: DESCRIPTIVE
  method: execution-grounded
  verified_at: 2026-06-29T03:06:23Z
links: [DIBEV_A]
---

# Age first told had diabetes (top-coded)

DIBAGETC_A is the age at which an adult was first told they had diabetes, asked only of
adults with diagnosed diabetes ([[DIBEV_A]] == 1) and top-coded at 85. Values of 96 and
above are non-substantive (refused / not ascertained / don't know) and must be dropped
before any age analysis. Any mean or distribution over this variable must be
survey-weighted (WTFA_A) and restricted to the DIBEV_A == 1 universe.

## Related
- [DIBEV_A](./DIBEV_A.md)
