# nhis-okf-compiler

Compile a messy, high-stakes public health dataset (**CDC NHIS**) into a *verified* **Open Knowledge Format (OKF)** bundle, with RAG-grounded search/chat over it — built with **Baton** orchestrating a **data-science domain skill**.

The point is not the chatbot. The point is that Baton's verify lane **executes the documented analysis against the real microdata** and catches a concept that is *structurally valid but statistically wrong* — a prevalence that ignores the survey weights, or a figure inflated because it skips a skip-pattern. The markdown is clean, every link resolves, and the number is still wrong; a passive RAG ships that confidently, Baton's cold-read reviewer runs it and catches it. **Execution-grounded verification, not link-checking.**

> **Status: lean slice built and verified (NHIS 2023, diabetes).** The end-to-end loop
> runs on real CDC microdata; the execution-grounded verifier catches a
> structurally-valid-but-statistically-wrong number that a link-check passes. Full plan in
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
./.venv/bin/nhis fetch      # download the NHIS 2023 Sample Adult public-use file
./.venv/bin/nhis verify     # execution-grounded verification of every concept
./.venv/bin/nhis compile    # emit the verified OKF bundle; quarantine failures
./.venv/bin/nhis query "what share of adults with diabetes take insulin?"
./.venv/bin/pytest -q
```

What the slice proves, on real data:

- **Correct:** 31.96% of U.S. adults with diagnosed diabetes currently take insulin
  (weighted by `WTFA_A`, universe `DIBEV_A == 1`).
- **The seeded defect:** a clean-markdown concept claims 3.66% (computed over the whole
  sample, unweighted). Its links resolve and the lint passes — but execution recomputes
  the correct 31.96% and **catches it (28.3pp off)**, quarantining it to `.okf/log.md`.
- The grounded query can only serve verified figures: 3.66% never enters the bundle.

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

## The shape

- **Baton owns the process** — discovery, the gated loop, execution-grounded verification, the audit trail.
- **A data-science domain skill owns the statistics** — survey weighting, skip-pattern logic, correctness. (Baton "prescribes nothing about other skills" — this is that thesis, made concrete and reusable across domains.)
- **OKF is the output** — markdown + YAML-frontmatter concepts, a markdown-link graph, `log.md` audit history. It is already Baton's native idiom.

## Two non-negotiables

- **Safety scope:** a tool to explore **public, de-identified, aggregate** survey data — *not* medical or clinical advice. No individual inference; every figure carries its survey-weighted basis and source.
- **Lean slice first:** one survey year, one topic (diabetes or hypertension), one verified analysis. Prove the loop end to end before scaling.
