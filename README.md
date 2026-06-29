# nhis-okf-compiler

Compile a messy, high-stakes public health dataset (**CDC NHIS**) into a *verified* **Open Knowledge Format (OKF)** bundle, with RAG-grounded search/chat over it — built with **Baton** orchestrating a **data-science domain skill**.

The point is not the chatbot. The point is that Baton's verify lane **executes the documented analysis against the real microdata** and catches a concept that is *structurally valid but statistically wrong* — a prevalence that ignores the survey weights, or a figure inflated because it skips a skip-pattern. The markdown is clean, every link resolves, and the number is still wrong; a passive RAG ships that confidently, Baton's cold-read reviewer runs it and catches it. **Execution-grounded verification, not link-checking.**

> **Status: built and verified (NHIS 2018 + 2023; diabetes and hypertension; design-based
> CIs).** Every verified figure carries a complex-survey 95% confidence interval. The
> end-to-end loop runs on real CDC microdata and the execution-grounded verifier catches
> three classes of
> structurally-valid-but-statistically-wrong number a link-check passes: a skip-pattern /
> weighting error within a year, and a broken cross-year trend from the 2019 redesign
> rename. The bundle conforms to the OKF v0.1 spec. Full plan in
> [docs/PRODUCT.md](docs/PRODUCT.md); next phase in
> [openspec/changes/build-end-to-end-nhis-okf](openspec/changes/build-end-to-end-nhis-okf/proposal.md).

## How it works

A query is answered through a verification funnel. The chat agent can only see concepts
that passed execution-grounded verification at compile time:

```
[ user query ]
      |
( Strands agent )            grounded-or-refuse; cites verified ids only
      |
[ search_verified_okf ]      the agent's only data tool
      |
( retrieval index )          TF-IDF over the verified bundle (local);
      |                       a Bedrock Knowledge Base from .okf/ on deploy
      +------------------------------+
      |                              |
      v                              v
 .okf/variables/                .okf/log.md
 DIBINS_A.md  -> 31.96%  PASS   DIBINS_A__naive -> 3.66%  QUARANTINED
      |                              |
      v                              v
 fed as context                 never indexed -> unreachable
```

`compiler.py` writes only verified concepts to `.okf/variables/` and quarantines failures
to `.okf/log.md`. Because the naive 3.66% figure is never written to the bundle, retrieval
cannot build an index row for it and the agent cannot surface it — grounding is enforced by
**what exists in the bundle**, not by prompt instructions alone.

Two consequences worth stating plainly:

- **Grounded-or-refuse.** Asked about a topic with no verified concept (e.g. asthma), the
  agent refuses and declines to invent a number, rather than stitching adjacent diabetes
  context into a best guess.
- **Local/cloud parity.** The same agent over the same OKF substrate runs on the Anthropic
  API (local) and on Bedrock `claude-sonnet-4-6` (deploy); only the model provider changes,
  so behaviour is identical across environments.

## Run it

```bash
python3 -m venv .venv && ./.venv/bin/pip install -e ".[dev]"
./.venv/bin/nhis fetch        # download the NHIS 2018 + 2023 Sample Adult public-use files
./.venv/bin/nhis verify       # execution-grounded verification of every concept
./.venv/bin/nhis trends       # cross-year verification (the 2019 redesign-rename catch)
./.venv/bin/nhis compile      # emit the verified OKF bundle; quarantine failures
./.venv/bin/nhis conformance  # check the bundle against the OKF v0.1 spec
./.venv/bin/nhis query "what share of adults with diabetes take insulin?"
./.venv/bin/pytest -q
```

What the slice proves, on real data — two classes of confidently-wrong number, each caught
and corrected:

- **Within-year (skip-pattern + weighting).** A clean-markdown concept claims 3.66% of
  adults take insulin (computed over the whole sample, unweighted). Its links resolve and
  the lint passes — but execution recomputes the correct figure and **catches it (28.3pp
  off)**, quarantines the 3.66% to `.okf/log.md`, and the bundle serves the **corrected
  31.96%** (weighted, universe `DIBEV_A == 1`). The wrong number is not just flagged — it is
  removed and replaced by the verified one.
- **Cross-year (the 2019 redesign rename).** A concept claims a flat ~9.8% diabetes trend
  by joining 2018 and 2023 on a single variable name. But the diabetes item was renamed
  (`DIBEV1` in 2018 → `DIBEV_A` in 2023), so that name does not exist in 2018 — the join
  silently drops a year. Execution catches the rename gap and quarantines it; the verified
  trend (`DIBEV1`/`WTFA_SA` in 2018, `DIBEV_A`/`WTFA_A` in 2023) is **10.09% → 9.80%**.
- The grounded query can only serve verified figures: neither quarantined number enters the
  bundle.
- **Generalizes to a second condition, no engine change.** Hypertension adds the same shape:
  32.26% of adults have it, and **79.62%** of those take BP medication (weighted, universe
  `HYPEV_A == 1`) — while the seeded whole-sample/unweighted claim of 30.98% is caught
  (48.6pp off) and quarantined. Same verifier, new variables.
- **Understated uncertainty (design-based CIs).** Every verified figure carries a
  complex-survey 95% CI from Taylor linearization (strata `PSTRAT`, PSU `PPSU`, weight
  `WTFA_A`) — e.g. diabetes 9.80% [9.39, 10.20], insulin 31.96% [30.08, 33.84]. A seeded
  concept with the *correct* point estimate but a simple-random-sampling CI (ignoring the
  design effect, DEFF ≈ 1.4) is caught for being **too precise** and quarantined. The CI math
  is hand-rolled and validated (point matches; DEFF > 1) rather than taken from a deprecated
  library — see the note below.

> **On the CI library:** the obvious choice (`samplics`) is archived/unmaintained and pulls
> in `polars`, which crashes under Rosetta on Apple Silicon. So the design-based variance is
> implemented directly (standard stratified, with-replacement Taylor linearization, ~20 lines
> of numpy) and validated by the property that proves it — the design effect exceeds 1.

### Chat (Strands + Bedrock AgentCore)

The chat is a **Strands agent** whose only data tool reads the *verified* OKF bundle, so it
is grounded-or-refuse: it cites verified concept ids, and refuses (rather than inventing a
number) when the bundle lacks the answer. Three modes:

- **Extractive** (default) — no key, no agent deps, fully grounded.
- **Strands / Anthropic API** (local testing) — `pip install -e ".[agent]"`, drop
  `ANTHROPIC_API_KEY` in `.env`, then `nhis query "..."` runs the agent.
- **Strands / Bedrock + AgentCore** (deploy) — `pip install -e ".[agent,deploy]"`; the
  agent runs on Bedrock (`config.bedrock_model_id`, default `claude-sonnet-4-6`) and is
  wrapped for the runtime in [`src/nhis_okf/agentcore_app.py`](src/nhis_okf/agentcore_app.py).
  Actual `agentcore`/CDK deploy is account-touching and gated.

Retrieval is a derived index over the verified bundle (TF-IDF today; embeddings or a
Bedrock Knowledge Base later). OKF stays the canonical substrate — only verified concepts
are ever indexed, so a quarantined figure can never be served.

## Sample queries (deployed on Bedrock AgentCore)

Real `agentcore invoke` responses from the deployed agent — it cites the concept id, quotes
the survey-weighted figure with its 95% CI, and refuses when the bundle has no answer. Full
transcript in [docs/SAMPLE.md](docs/SAMPLE.md).

**Refusal — off-bundle:**
> Q: *what is the prevalence of asthma among US adults?*
> A: I cannot answer this from the verified NHIS bundle — no verified concept for asthma.

**Grounded, and honest about its limits:**
> Q: *how does survey weighting change diabetes prevalence?*
> A: 9.8% (95% CI 9.39–10.20) **[DIBEV_A]**, DEFF 1.41 … but I cannot give the
> weighted-vs-unweighted difference — it is not a verified concept in the bundle.

Asked the same weighting question, an ungrounded frontier model invented an unweighted 11.2%,
race/age subgroup tables, and a false claim about the bundle. The grounded agent refused to
state the unweighted number even though it is real — because it is not verified here. Grounding
makes it *less* willing to guess.

## The shape

- **Baton owns the process** — discovery, the gated loop, execution-grounded verification, the audit trail.
- **A data-science domain skill owns the statistics** — survey weighting, skip-pattern logic, correctness. (Baton "prescribes nothing about other skills" — this is that thesis, made concrete and reusable across domains.)
- **OKF is the output** — markdown + YAML-frontmatter concepts, a markdown-link graph, `log.md` audit history. It is already Baton's native idiom.

## Two non-negotiables

- **Safety scope:** a tool to explore **public, de-identified, aggregate** survey data — *not* medical or clinical advice. No individual inference; every figure carries its survey-weighted basis and source.
- **Lean slice first:** one survey year, one topic (diabetes or hypertension), one verified analysis. Prove the loop end to end before scaling.
