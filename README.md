# nhis-okf-compiler

Compile a messy, high-stakes public health dataset (**CDC NHIS**) into a *verified* **Open Knowledge Format (OKF)** bundle, with RAG-grounded search/chat over it — built with **Baton** orchestrating a **data-science domain skill**.

The point is not the chatbot. The point is that Baton's verify lane **executes the documented analysis against the real microdata** and catches a concept that is *structurally valid but statistically wrong* — a prevalence that ignores the survey weights, or a figure inflated because it skips a skip-pattern. The markdown is clean, every link resolves, and the number is still wrong; a passive RAG ships that confidently, Baton's cold-read reviewer runs it and catches it. **Execution-grounded verification, not link-checking.**

> **Status: lean slice built and verified (NHIS 2023, diabetes).** The end-to-end loop
> runs on real CDC microdata; the execution-grounded verifier catches a
> structurally-valid-but-statistically-wrong number that a link-check passes. Full plan in
> [docs/PRODUCT.md](docs/PRODUCT.md); next phase in
> [openspec/changes/build-end-to-end-nhis-okf](openspec/changes/build-end-to-end-nhis-okf/proposal.md).

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

Generative chat is scaffolded and key-gated; without a key the extractive answer is fully
grounded in the verified bundle. Drop `ANTHROPIC_API_KEY` into `.env` to enable generation.

## The shape

- **Baton owns the process** — discovery, the gated loop, execution-grounded verification, the audit trail.
- **A data-science domain skill owns the statistics** — survey weighting, skip-pattern logic, correctness. (Baton "prescribes nothing about other skills" — this is that thesis, made concrete and reusable across domains.)
- **OKF is the output** — markdown + YAML-frontmatter concepts, a markdown-link graph, `log.md` audit history. It is already Baton's native idiom.

## Two non-negotiables

- **Safety scope:** a tool to explore **public, de-identified, aggregate** survey data — *not* medical or clinical advice. No individual inference; every figure carries its survey-weighted basis and source.
- **Lean slice first:** one survey year, one topic (diabetes or hypertension), one verified analysis. Prove the loop end to end before scaling.
