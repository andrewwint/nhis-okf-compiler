# Change: Researcher row-level query tool + OKF usage instructions

## Why

Analysts sometimes need to inspect the underlying **rows** of the public-use microdata —
pull specific columns for a subpopulation to reproduce or sanity-check a figure — not just
the survey-weighted aggregate. NHIS public-use files are de-identified and top-coded
precisely so row inspection is safe (that is their intended use), so a research tool that
returns rows is legitimate. What must be protected is the *verified-answer* product: raw,
unweighted rows must never surface through the verified query path or the deployed grounded
agent, where an unweighted number would be mistaken for a population estimate — the exact
defect this project exists to catch.

This change adds that researcher tool as a **separate, clearly-labeled surface**, and — per
the canonical OKF model — documents how to use it inside the OKF bundle, so a researcher or
agent reads the bundle as a map to the tool.

## What Changes

- **`parquet_query.py` + `nhis rows`.** A researcher tool that returns selected columns of
  the rows matching an arbitrary universe, read from the parquet-preferring load path. It
  requires explicit `--columns` (no accidental full dump), bounds output with `--limit` (a
  capped default), and prints a loud header on every call: the records are **raw,
  unweighted, de-identified public-use data — for research inspection, not population
  estimates, not verified**; use `nhis analyze` for weighted figures. This is the one
  surface that returns rows, by design.
- **OKF usage instructions.** The bundle gains a `references/parquet_query.md` **Reference**
  concept documenting the tool, the weight/universe caveats, and how to move from a raw-row
  inspection to a verified aggregate. Each analytical variable concept also gains a
  `# Reproduce` section carrying the exact `nhis analyze` (weighted) and `nhis rows` (raw)
  invocations — so every OKF concept is both a verified answer and a runnable recipe.
- **Boundary hardening.** The verified query path (`nhis analyze`, grounded-or-refuse) and
  the deployed grounded agent (`chat.py`, `agentcore_app.py`) stay aggregate-only and MUST
  NOT import or reach the row tool. The safety copy is updated to distinguish the verified
  product (no individual-level inference) from the local researcher tool (public
  de-identified microdata inspection), so the documented scope stays honest.

## Impact

- Affected specs: `okf-compiler` (ADDED: researcher row-query tool; ADDED: OKF tool-usage
  instructions).
- Affected code: new `src/nhis_okf/parquet_query.py`, `cli.py` (`nhis rows`),
  `compiler.py` (emit the Reference concept + per-concept `# Reproduce` block), new
  `concepts/references/parquet_query.yaml` (or equivalent source), safety copy in `chat.py`
  and `CLAUDE.md`, `tests/`.
- Out of scope (deferred): exposing rows through `nhis analyze` or the deployed agent
  (explicitly rejected); restricted-use (non-public) NHIS files; a web surface.
