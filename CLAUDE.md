# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

The **lean diabetes slice (NHIS 2023) is built and verified.** The end-to-end loop runs on
real CDC microdata and the execution-grounded verifier catches a
structurally-valid-but-statistically-wrong number that a link-check passes.

Commands (use the project venv):

```bash
python3 -m venv .venv && ./.venv/bin/pip install -e ".[dev]"
./.venv/bin/nhis fetch | verify | compile | query "..."   # see README
./.venv/bin/pytest -q                                       # 14 tests
```

Source lives in `src/nhis_okf/` (registry, analysis, concepts, verify, compiler,
retrieval, chat, cli); concepts in `concepts/*.yaml`; the verified bundle in
`.okf/variables/` with `.okf/log.md`; the project-local domain skill in
`.claude/skills/data-science/`. The next phase is planned in
`openspec/changes/build-end-to-end-nhis-okf/`.

**One agent, one deploy project.** The AgentCore runtime runs the real
`src/nhis_okf/agentcore_app.py` (never a reimplementation) over the committed `.okf/`
bundle. The deploy is a single AgentCore CLI project at the repo root: `agentcore/`
(config: `agentcore.json`, `aws-targets.json`) + `app/nhis_okf_chat/` (a thin `main.py`
re-exporting the agent + a `pyproject.toml` that installs `nhis_okf` as a dependency). Deploy
with the `agentcore` CLI (`agentcore deploy`/`invoke`); demo is CLI-only (no web front). Do
not reintroduce a parallel agent or a committed duplicate bundle. The runtime packages
retrieval-only (pandas is an optional `[compute]` extra, kept out of the CodeZip); porting
query-time compute into the runtime for live tables needs a **container** build — the CodeZip
limit is 250 MB compressed / 750 MB uncompressed.

The authoritative plan is `docs/PRODUCT.md`. Read it before substantive work; the sections
below summarize what constrains implementation.

## What this project is

Compile a messy, high-stakes public-health dataset (**CDC NHIS** — National Health Interview Survey) into a **verified Open Knowledge Format (OKF)** bundle, with RAG-grounded search/chat over it. The build is orchestrated by **Baton** (an external orchestrator that lives in its own repo) composed with a **project-local data-science domain skill**.

Division of responsibility (the composition thesis — keep these separate):
- **Baton** owns *process*: discovery, the gated loop, execution-grounded verification, and the audit trail. Stays domain-agnostic.
- **The data-science skill** owns *statistics*: survey weighting, skip-pattern/universe logic, statistical correctness.
- **OKF** is the *output*: markdown + YAML-frontmatter concept files, a markdown-link graph between them, and a `log.md` audit history.

## The non-negotiable constraint (do not soften)

**Verification must EXECUTE, not lint.** Link-checking and universe-documentation are cheap pre-checks a script owns. The gate that justifies the project **runs the documented analysis against the real NHIS microdata with proper survey weights and confirms the number matches the claim.**

The headline defect to catch is a concept whose links all resolve and whose markdown is clean, but whose documented analysis produces the **wrong number** when actually run. Concrete defect classes in the diabetes slice:
- **Skip-pattern / universe error.** The insulin item (`DIBINS_A` in NHIS 2023; `INSLN_A` in older years) is a skip-pattern question, empirically asked of adults with diabetes *or* prediabetes (`(DIBEV_A == 1) | (PREDIB_A == 1)`) — not the whole sample. A naive "% taking insulin" over the whole sample is badly **deflated** (the un-asked read as non-users); it must be "% among diagnosed adults" (`DIBEV_A == 1`), survey-weighted. Built result: naive 3.66% vs correct 31.96% — caught by execution.
- **Redesign rename.** The 2019 NHIS redesign renamed `DIBEV` → `DIBEV_A`. A longitudinal join that ignores the rename produces a broken trend.

If every catch the demo produces is "broken link / dead ref," the project failed — that is a linter, not the point. The point is the number that is confidently wrong.

Survey weights are **mandatory**, not optional — naive unweighted counts are simply wrong for NHIS.

## Planned structure (per docs/PRODUCT.md — not yet created)

- `.claude/skills/data-science/SKILL.md` — the "epidemiological data engineer → OKF" specialist skill, authored via **skill-creator**. Kept **project-local for now**; extract to a portable skill only if NHANES/BRFSS reuse materializes (specific-first, generalize-later).
- `raw_codebooks/` — target NHIS Sample Adult codebooks / layout files.
- `.okf/variables/` — the compiled, verified knowledge base, one markdown file per variable (e.g. `DIBEV_A.md`, `DIBAGE_A.md`, `INSLN_A.md`) plus a master `log.md`.

## Scope guardrails

- **Lean slice first.** One survey year, one topic (**diabetes**, decided), a handful of variables, **one** verified weighted-prevalence analysis. Prove the loop end-to-end (compile → execution-verify catches a wrong stat → grounded answer cites the verified concept) before scaling years/topics. Do not compile all of NHIS.
- **Safety scope.** Two surfaces, kept distinct. The **verified product** (`nhis analyze`, `nhis query`, and the deployed grounded agent) explores **public, de-identified, aggregate** survey data — *not* medical or clinical advice, no individual-level inference, no health recommendations; every figure carries its survey-weighted basis and source. That guarantee is unchanged and aggregate-only: the agent cannot access or return individual records. The **local researcher tool** (`nhis rows`) is the one surface that returns raw rows — a few columns of the **public, de-identified, top-coded** public-use microdata, for local research inspection (row inspection is that file's intended use). Its rows are raw and **unweighted** — never population estimates — so it prints a loud caveat on every call and stays out of the verified product and the agent (enforced by an import-boundary test).
- **Avoid premature abstraction.** Keep it one repo with a project-local skill; do not build the "portable across health datasets" layer until the diabetes slice earns it.
