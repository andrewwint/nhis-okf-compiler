# OKF audit log

Compiled from NHIS 2023 Sample Adult public-use file (adult23.csv).
Last run: 2026-06-29T03:22:56Z

Every concept is verified by *executing* its analysis against the real
microdata with proper survey weights — not by checking links. Quarantined
concepts failed that check and were kept out of the trusted bundle.

| concept | verdict | claimed | correct | delta (pp) | note |
| --- | --- | --- | --- | --- | --- |
| DIBAGETC_A | DESCRIPTIVE | — | — | — | documented (no executable statistic) |
| DIBEV_A | PASS | 9.8 | 9.8 | 0.0 |  |
| DIBINS_A | PASS | 31.96 | 31.96 | 0.0 |  |
| DIBINS_A__naive | FAIL | 3.66 | 31.96 | 28.3 | QUARANTINED — lint passed, execution caught it: method is UNWEIGHTED; NHIS estimates require survey weights (WTFA_A); universe is 'whole sample'; correct analytical universe is 'DIBEV_A == 1' |
