# Change: Agent row-inspection tool grounded in OKF column summaries (local slice)

## Why

Test the OKF thesis end to end: can the OKF bundle drive an agent that does **row-level
querying** *and* explains what it returned using **OKF's verified column summaries**? The
concept files already carry each column's meaning (label, valid codes, universe, prose); this
wires a bounded row surface into the local agent that returns capped/caveated rows alongside
the OKF summary for each column — the canonical "OKF as the schema/map for the agent" story.

This is the **local, no-AWS slice** that validates the capability. The S3 + AgentCore Code
Interpreter deploy is a separate, later phase (its contract is already read).

## What Changes

- **A deliberate, bounded scope change** (approved): the local agent gains a raw-row surface.
  It is capped (≤12 columns, hard row cap), carries the mandatory
  RAW·UNWEIGHTED·NOT-a-population-estimate banner, and attaches each returned column's
  **verified OKF concept summary** (label, valid codes + meaning, universe). Aggregate answers
  keep the verified-aggregate guarantee.
- **Deploy stays aggregate-only.** The row tool registers only in the **default** tool set;
  `NHIS_RUNTIME_TOOLS=retrieval` (the deployed mode) does **not** get it, and `query_rows`/
  `analysis` stay lazy-imported so the retrieval CodeZip remains pandas-free. The deployed
  agent is unchanged by this slice.
- **Harden the universe eval (`injection-sink`).** `analysis._mask` uses `df.eval` on the
  universe string; exposed via an agent tool, a crafted string could reach Python builtins.
  Add an allow-list validator (permit only `COLUMN <comparison> NUMBER` joined by `& | ( )`;
  reject names/attributes/calls/anything else) applied on the agent path. Existing universes
  (`DIBEV_A == 1`, `(DIBEV_A == 1) | (PREDIB_A == 1)`, `SEX_A == 2`, …) must still parse.
- **Framing updated** in README/SAMPLE/CLAUDE.md: the surface serves raw public-use records
  for inspection with their OKF column summaries; they are not population estimates.

## Impact

- Affected specs: `okf-compiler` (ADDED: OKF-grounded row inspection; MODIFIED: the agent may
  expose a bounded, caveated row surface in default mode only).
- Affected code: `chat.py` (row tool + prompt + tool-mode gating), `analysis.py`/
  `parquet_query.py` (universe allow-list), `registry.py`/retrieval (column-summary lookup),
  tests, README/SAMPLE/CLAUDE.md.
- Sensitive seam: `injection-sink@universe-eval` — owed a security-review disposition.
- Out of scope: S3, IAM, the Code Interpreter deploy (phase 2); any change to the deployed
  retrieval-only runtime.
