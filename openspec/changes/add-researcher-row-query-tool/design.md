## Context

The verified product answers with survey-weighted aggregates and refuses to leak rows. A
research workflow sometimes needs the underlying rows of the public-use microdata to
reproduce or inspect a figure. This change adds that as a separate tool and documents it in
the OKF bundle, without weakening the verified path.

## Goals / Non-Goals

- Goals: a labeled `nhis rows` researcher tool that returns selected columns; OKF
  instructions (a Reference concept + per-concept `# Reproduce` blocks) so the bundle maps a
  researcher/agent to the tool; an honest safety scope that names both surfaces.
- Non-Goals: rows through `nhis analyze` or the deployed agent; restricted-use files; a web
  API; unweighted numbers presented as population estimates anywhere in the verified path.

## Decisions

- **Row return is safe here because the data is public and de-identified.** NHIS public-use
  files are top-coded/coarsened to prevent re-identification; row inspection is their
  intended use. The row tool operates only on that public file.
- **One surface returns rows, and it is loudly labeled.** `nhis rows` is the sole path that
  emits individual records, and every invocation prints a raw/unweighted/not-verified
  caveat. This keeps the boundary legible rather than blurring it into `nhis analyze`.
- **The row tool is deliberately NOT grounded-or-refuse.** Its purpose is raw inspection, so
  it may pull any column, not only verified-concept variables. That is the opposite of the
  verified path on purpose — and precisely why it must stay out of the verified product and
  the agent.
- **The agent boundary is enforced, not just documented.** A test asserts `chat.py` and
  `agentcore_app.py` do not import `parquet_query`, so the deployed grounded agent cannot
  reach row output even by mistake.
- **OKF documents the tool (the canonical OKF model).** A `references/parquet_query.md`
  Reference concept plus per-concept `# Reproduce` blocks make each concept both a verified
  answer and a runnable recipe — the "map for the agent" the user expected of OKF, pointed
  at the research tool rather than the verified chatbot.
- **Explicit columns + a row cap.** Requiring `--columns` and enforcing a `--limit` cap
  prevents an accidental full-microdata dump and keeps the tool a deliberate, scoped
  inspection rather than an export firehose.

## Risks / Trade-offs

- Someone treats raw `nhis rows` output as a population estimate → the mandatory caveat
  header and the OKF Reference concept both state it is unweighted and not verified, and
  point to `nhis analyze` for weighted figures.
- Documented "no individual-level inference" scope now coexists with a row tool → resolved
  by updating the copy to scope that guarantee to the verified product, while naming the
  researcher tool as public-microdata inspection. The product guarantee is not weakened.

## Migration Plan

Additive. New module, new CLI subcommand, a new Reference concept, and per-concept
`# Reproduce` blocks; the verified query path, the agent, and all existing concepts keep
their behavior.

## Open Questions

- Whether the `# Reproduce` block should also appear on descriptive concepts (deferred —
  start with analytical concepts, which have a concrete universe/statistic to reproduce).
