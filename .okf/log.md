# OKF audit log

Compiled from NHIS 2023 Sample Adult public-use file (adult23.csv).
Last run: 2026-06-29T04:44:31Z

Every concept is verified by *executing* its analysis against the real microdata
with proper survey weights — not by checking links. Quarantined concepts failed
that check and were kept out of the trusted bundle.

| concept | verdict | claimed | correct | delta (pp) | note |
| --- | --- | --- | --- | --- | --- |
| DIBAGETC_A | DESCRIPTIVE | — | — | — | documented (no executable statistic) |
| DIBEV_A | PASS | 9.8 | 9.8 | 0.0 |  |
| DIBINS_A | PASS | 31.96 | 31.96 | 0.0 |  |
| DIBINS_A__naive | FAIL | 3.66 | 31.96 | 28.3 | QUARANTINED — lint passed, execution caught it: method is UNWEIGHTED; NHIS estimates require survey weights (WTFA_A); universe is 'whole sample'; correct analytical universe is 'DIBEV_A == 1' |

## Cross-year trends (2019 redesign-rename catch)

| trend | verdict | note |
| --- | --- | --- |
| TREND_diabetes_2018_2023 | PASS |  |
| TREND_diabetes__naive | FAIL | QUARANTINED — lint passed, execution caught it: 2018: variable 'DIBEV_A' is not in the data — it was renamed in the 2019 redesign; the correct 2018 variable is 'DIBEV1'. A single-name join drops 2018, producing a broken trend. |
