# nhis-okf-compiler

Compile a messy public-health dataset (CDC NHIS) into a *verified* Open Knowledge Format
(OKF) bundle, with a local and cloud-ready RAG search/chat over it — built with **Baton**
orchestrating a project-local data-science domain skill.

The point is execution over syntax. Baton's verify lane runs each documented analysis against
the real microdata and catches concepts that are structurally clean but statistically wrong —
a prevalence that ignores survey weights, or a figure that breaks a skip-pattern boundary. A
passive RAG ships those confidently; here they are quarantined before they reach the index.

**Status:** built and verified. NHIS 2018 + 2023, diabetes and hypertension, with design-based
95% confidence intervals; the bundle conforms to the OKF v0.1 spec. Public, aggregate survey
data only — not medical advice.

## How it works

A query passes through a verification funnel. The agent only ever sees concepts that passed
execution-grounded verification at compile time:

```
[ user query ]
      |
( Strands agent )         grounded-or-refuse; cites verified ids only
      |
[ search_verified_okf ]   the agent's only data tool
      |
( retrieval index )       in-process retrieval over the verified bundle —
      |                   the same mechanism locally and when deployed
      +------------------------------+
      |                              |
      v                              v
 .okf/variables/                .okf/log.md
 DIBINS_A.md -> 31.96%  PASS    DIBINS_A__naive -> 3.66%  QUARANTINED
      |                              |
      v                              v
 fed to the agent               never indexed -> unreachable
```

`compiler.py` writes only verified concepts to `.okf/variables/` and quarantines failures to
`.okf/log.md`. A quarantined figure is never written to the bundle, so the retriever cannot
build an index entry for it — grounding is enforced by what exists, not by prompt instructions.

## Zero-database RAG

A typical production RAG needs a vector database, a chunking service, and an embeddings
endpoint to handle uncurated documents:

```
[ unverified docs ] -> [ chunker ] -> [ embeddings API ] -> [ vector DB ] -> [ LLM context ]
```

Because verification curates the corpus upstream — at compile time — none of that is required:

```
[ raw microdata ] -> [ Baton execution gate ] -> [ verified .okf/ markdown ] -> [ in-process TF-IDF ] -> [ LLM context ]
```

- **The substrate is the index.** Retrieval is dependency-light, in-process TF-IDF directly
  over the `.okf/variables/` folder. Grounding comes from the physical absence of quarantined
  files, not from vector math or prompt heuristics.
- **Local-to-cloud parity.** The bundle is a flat folder of conformant markdown, so the same
  substrate runs locally (Anthropic API) and deploys straight to Amazon Bedrock AgentCore
  (Claude Sonnet 4) with identical lookup mechanics — no drift between environments.
- **No retrieval infrastructure.** No vector cluster to provision, no index sync, no
  embedding-endpoint latency; the index runs in-memory in the Python process. A managed vector
  store (e.g. a Bedrock Knowledge Base) is an optional scale-up, not a requirement. Only
  retrieval is self-contained — answer generation still calls the model API.

Proven live: the bundle deployed to Bedrock AgentCore, answered with verified figures, refused
off-bundle questions, then was torn down. Transcript in [docs/SAMPLE.md](docs/SAMPLE.md).

## Getting started

```bash
python3 -m venv .venv && ./.venv/bin/pip install -e ".[dev]"
./.venv/bin/nhis fetch        # NHIS 2018 + 2023 Sample Adult public-use files
./.venv/bin/nhis verify       # execution-grounded verification
./.venv/bin/nhis trends       # cross-year checks (the 2019 redesign-rename catch)
./.venv/bin/nhis compile      # emit the verified OKF bundle; quarantine failures
./.venv/bin/nhis conformance  # check against the OKF v0.1 spec
./.venv/bin/nhis query "what share of adults with diabetes take insulin?"
./.venv/bin/pytest -q         # 41 tests
```

The raw inputs are the CDC NHIS Sample Adult **public-use CSV files** (`samadult.csv` for 2018,
`adult23.csv` for 2023) — a few tens of MB each, fetched from the CDC by `nhis fetch` and not
committed to the repo. Verification runs the documented analyses directly against these files;
the compiled `.okf/` bundle is the only thing derived from them.

Agent path: `pip install -e ".[agent]"`, drop `ANTHROPIC_API_KEY` in `.env`, then `nhis query`
runs the Strands agent. Deploy notes in [deploy/README.md](deploy/README.md).

## What the verification catches

Four classes of clean-but-wrong number, each caught by *running* the analysis — three distinct
kinds, plus a second condition that shows the check generalizes.

**1. Skip-pattern + weighting (within a year).** A concept computes insulin use over the whole
sample, unweighted, claiming **3.66%**. Recomputed with the mandatory weight (`WTFA_A`) and the
correct universe (`DIBEV_A == 1`), it is **31.96%** — off by 28 points. The 3.66% is
quarantined; the bundle serves 31.96%.

**2. Cross-year trend (the 2019 redesign rename).** A trend joins 2018 and 2023 by one variable
name and reads as a flat ~9.8%. But the item was renamed (`DIBEV1` → `DIBEV_A`), so the name is
absent in 2018 and the join silently drops a year. The verifier flags the gap; the verified
trend is **10.09% → 9.80%**.

**3. Understated uncertainty (design-based CIs).** A concept has the right point estimate but a
simple-random-sampling CI that ignores the survey's clustering. Stratified, with-replacement
Taylor linearization (~20 lines of NumPy over `PSTRAT`/`PPSU`) recomputes it, and an
over-precise interval is caught (design effect > 1):
- diabetes prevalence **9.80%** [9.39, 10.20] (DEFF 1.41)
- insulin use **31.96%** [30.08, 33.84]

**Generalizes to a second condition, no engine change.** Hypertension: 32.26% prevalence,
**79.62%** on BP medication among those with hypertension (`HYPEV_A == 1`); the naive
whole-sample/unweighted claim of 30.98% is caught (48.6 points off) and quarantined. Same
verifier, new variables.

> The `samplics` survey library was dropped — it is archived and crashes under Rosetta on
> Apple Silicon — so the variance math is implemented directly in NumPy and validated by the
> design-effect > 1 property.

## Grounded vs ungrounded

Asked *"how does survey weighting change diabetes prevalence?"*, an ungrounded frontier model
invented an unweighted 11.2%, fabricated race/age subgroup tables, and a false claim about this
project's internals. The grounded agent returned the verified **9.8% [DIBEV_A]** and **declined**
the weighted-vs-unweighted comparison — because it is not a verified concept in the bundle.
Grounding makes the agent less willing to guess. Full transcript: [docs/SAMPLE.md](docs/SAMPLE.md).

## The pieces

- **Baton** — orchestration: discovery, the gated compile pipeline, execution-grounded
  verification, the audit trail.
- **Data-science domain skill** (project-local) — the statistics: survey weights,
  skip-pattern/universe logic, variance.
- **OKF v0.1** — the output: markdown + YAML-frontmatter concepts, a markdown-link graph, a
  `log.md` audit history.
- **Safety scope** — public, de-identified, aggregate survey data only; no individual-level
  inference and no medical advice; every figure carries its survey-weighted basis and source.

Full plan in [docs/PRODUCT.md](docs/PRODUCT.md); next phase in
[openspec/changes/build-end-to-end-nhis-okf](openspec/changes/build-end-to-end-nhis-okf/proposal.md).
