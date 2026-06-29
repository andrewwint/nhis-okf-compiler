---
name: data-science
description: >
  Epidemiological data engineer for compiling CDC NHIS (and similar complex-survey
  health data) into a verified Open Knowledge Format bundle. Use when the work involves
  NHIS variables, survey weights, skip-patterns/universes, prevalence estimates, or
  turning a statistical codebook into verified knowledge concepts. Owns statistical
  correctness; Baton owns process and the gated loop.
---

# Data science: NHIS → verified OKF

This is the project-local specialist skill that Baton composes with. The division of
responsibility is the point of the project:

- **Baton owns process** — discovery, the gated loop, the audit trail, and *running* the
  verification step.
- **This skill owns statistics** — survey weighting, skip-pattern/universe logic, and
  what "correct" means for an NHIS estimate.

Kept project-local for now (specific-first). Generalize to NHANES/BRFSS only if reuse
materializes — do not pre-build the portable layer.

## The one non-negotiable rule

**Verification must EXECUTE, not lint.** Checking that markdown is well-formed and links
resolve is a cheap pre-check a script owns (`verify.lint_concept`). It is not the gate.
The gate that justifies the project **runs the documented analysis against the real
microdata with proper survey weights and confirms the claimed number** (`verify.verify_concept`).

A concept can have clean markdown, resolving links, and a number you can reproduce from
its own stated method — and still be wrong. That is exactly what to catch. If every catch
is "broken link," the skill has failed: that is a linter, not this.

## Survey-correctness rules (the statistics this skill owns)

1. **Weights are mandatory.** NHIS Sample Adult estimates use `WTFA_A`. An unweighted
   count does not estimate the U.S. population — treat "unweighted" as a defect, not a
   simplification.
2. **Respect the universe (skip-pattern).** Many items are only asked of a subgroup. The
   denominator must be the universe the *claim* targets, not the whole sample and not
   automatically the full question universe. Confirm the universe **empirically** against
   the data (who actually has a non-missing answer), not from the variable name.
   - Example: `DIBINS_A` (insulin) is asked of adults with diabetes *or* prediabetes, but
     the claim "insulin use among diagnosed diabetics" has denominator `DIBEV_A == 1`.
3. **Drop non-substantive codes.** 7/8/9 (and 96–99 for continuous items like
   `DIBAGETC_A`) are Refused / Not Ascertained / Don't Know — never valid analysis values.
4. **Design-based variance is the documented upgrade.** Point estimates use weights;
   proper confidence intervals need Taylor linearization with `PSTRAT`/`PPSU`. The lean
   slice reports weighted point estimates and records the design variables; CIs come next.

## Compiling a variable into an OKF concept

1. Add the variable's ground truth to `src/nhis_okf/registry.py`: label, valid codes,
   affirmative codes (for yes/no rates), the **universe expression** (confirmed
   empirically), and the weight. The registry is the *independent* source of truth the
   verifier trusts — never the concept's own claimed method.
2. Author a concept in `concepts/<ID>.yaml`: prose, links, and (for analytical concepts)
   a headline statistic with its stated method and claimed value.
3. Run `nhis verify` — it recomputes the correct way and compares. Then `nhis compile`
   writes only passing concepts to `.okf/variables/` and quarantines failures to
   `.okf/log.md`.

## Defect classes to seed and catch (proof the gate works)

- **Whole-sample denominator** — computing a skip-pattern item over everyone (deflates
  the rate massively). The seeded `DIBINS_A__naive` concept demonstrates this.
- **Unweighted estimate** — ignoring `WTFA_A`.
- **Wrong analytical universe** — using the full question universe when the claim targets
  a narrower subgroup (e.g. including prediabetics in "among diagnosed diabetics").
- **Redesign rename across years** — the 2019 NHIS redesign renamed `DIBEV` → `DIBEV_A`;
  a longitudinal join that ignores it breaks the trend. (A later multi-year expansion.)
