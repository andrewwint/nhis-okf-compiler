## Context

Test whether OKF can drive an agent that does row-level querying grounded in OKF's verified
column summaries. The pieces exist — `query_rows` (capped/caveated rows) and the verified
concepts (column meaning) — this joins them behind a bounded agent tool, locally, no AWS.

## Goals / Non-Goals

- Goals: a bounded, caveated row-inspection tool in the local agent that returns rows + the
  OKF column summary; the universe eval hardened against injection; deploy stays aggregate-only.
- Non-Goals: S3/IAM/Code-Interpreter deploy (phase 2); changing the deployed retrieval runtime;
  any un-caveated raw dump; weighted claims off raw rows.

## Decisions

- **Deploy stays aggregate-only; this is a default-mode-only change.** The row tool registers
  only when `NHIS_RUNTIME_TOOLS` != retrieval. The deployed agent runs retrieval mode and is
  pandas-free, so it neither registers nor can execute the tool. The article's "verified
  aggregate, no vector DB" deploy claim is untouched; the row surface is a local capability now,
  a Code-Interpreter phase-2 feature later.
- **Rows are the *means*, OKF summary is the *grounding*.** The tool returns raw rows (the tested
  capability) but pairs every column with its verified concept summary (label, codes, universe),
  so the agent explains what it returned from OKF — not from guessing. A column with no verified
  concept says so; it never fabricates a meaning.
- **Harden the universe eval, don't remove it.** `_mask`'s `df.eval` is safe for repo-authored
  universes but becomes an injection sink once an agent composes the string. Add an allow-list
  (COLUMN comparison NUMBER, joined by boolean/parens) on the agent path; existing CLI/concept
  universes are all in this grammar, so nothing valid breaks. This is the seam the security-review
  lane judges.
- **Re-express the boundary, don't delete it.** The "agent can't reach rows" guarantee becomes
  "the *deployed* (retrieval) agent can't reach rows, and any row output is capped + caveated" —
  a narrower, still-meaningful invariant, tested.

## Risks / Trade-offs

- Allow-list too strict → a valid universe is rejected: cover the existing universes + boolean
  combos in tests; keep the grammar exactly as wide as those need.
- Scope-creep into the deployed product: gating on `NHIS_RUNTIME_TOOLS` + pandas-free retrieval
  is the guard; a test asserts retrieval mode has no row tool.
- The `df.eval` injection surface is real (see the Code-Interpreter contract-read); the allow-list
  is the mitigation and is the security-review lane's subject.

## Migration Plan

Additive tool + a hardened eval path + a re-expressed boundary test + framing. The CLI, the
verification engine, and the deployed retrieval runtime keep their behavior.

## Open Questions

- Whether to also surface the OKF summary in the CLI `nhis rows` output (nice, but the agent is
  the thing under test) — defer unless trivial.
