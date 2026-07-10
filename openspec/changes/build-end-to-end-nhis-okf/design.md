# Design notes: end-to-end NHIS-OKF

## Context

The lean slice established the spine: a registry of ground-truth domain knowledge, an
explicit prevalence engine that can express both correct and flawed methods, a verifier
that recomputes the correct way and compares to the claim, a compiler that quarantines
failures, and local grounded retrieval. The end-to-end build extends that spine without
changing its shape.

## Decisions

- **Keep the registry as the independent source of truth.** Verification must never trust
  the method a concept claims. Every new defect class (wrong universe, unweighted, wrong
  denominator mode, broken cross-year join, fabricated generative answer) is caught by
  comparing against an independent correct computation, not by re-running the claim.

- **Extend the one engine; do not fork it.** Means/quantiles and design-based variance are
  added to `analysis.py` as new computations behind the same explicit-knobs pattern, so a
  flawed method stays expressible (and therefore catchable). Resist a separate "stats
  library" abstraction until a second dataset needs it.

- **Design-based variance via Taylor linearization.** Point estimates only need weights;
  correct intervals need `PSTRAT`/`PPSU`. Prefer a small, transparent implementation (or a
  vetted survey package) over hand-rolled approximations — a wrong CI is its own
  confidently-wrong number.

- **Cross-year rename is a first-class defect, not a footnote.** The registry carries a
  rename map; the verifier treats a single-name multi-year join across the 2019 redesign as
  a defect and reports the gap. This is the second marquee catch the product promises.

- **Codebook ingestion feeds discovery but never bypasses verification.** Auto-parsed
  drafts are proposals; only execution-verified concepts enter the trusted bundle. An
  unconfirmed universe is held, not published.

- **Generative answering is grounded-or-refuse.** The key lights up generation, but the
  guard (cite-only-verified, no invented numbers, refuse outside the bundle) is what keeps
  it honest. Extractive remains the keyless default.

## Risks / tradeoffs

- **`df.eval` on universe strings** is safe while concepts are repo-authored and local. If
  codebook ingestion or a UI ever introduces untrusted input, replace it with a parsed,
  allow-listed predicate (already noted in `analysis.py`).
- **Variance correctness is high-stakes.** Treat the CI implementation as a verification
  target itself (compare against a known reference on a fixed slice).
- **Scope creep toward a portable multi-dataset layer** is the main temptation. Defer it;
  the value is proven on one dataset done correctly.
