# Product plan: nhis-okf-compiler (Baton Run 9)

A Baton dogfood **and** a real tool: compile a messy, high-stakes public health dataset (CDC NHIS) into a *verified* Open Knowledge Format (OKF) bundle, with a RAG-grounded search/chat over it. Baton orchestrates the build and composes with a **data-science domain skill**; its verify lane does **execution-grounded** checking, not link-checking.

Status: **product planning, active** (unlike the on-hold `review-discipline-eval` study, this one we intend to build).

---

## 1. Why this project

- **Fits the domain.** Data science over regulated, high-integrity health data is the maintainer's background and Baton's brand (auditable, gated, data-residency-friendly, local-first).
- **Real problem.** Standard agents hallucinate relationships in massive, messy government codebooks: NHIS variables rename across years, survey skip-patterns change, and **weights are mandatory** (naive counts are simply wrong). A chatbot grounded on raw PDFs gives confidently-wrong statistics.
- **Baton's verify lane does its *real* job here** — not link-checking (a script owns that), but **executing** the documented analysis against the real microdata and catching a concept that is *structurally valid but statistically wrong*. That is the thesis applied to data work.
- **Showcases composition.** Baton owns process / verify / audit; a **data-science domain skill** owns survey weighting, skip-pattern logic, and statistical correctness. A reusable pattern across domains.

## 2. The differentiator (hard constraint — do not soften)

Verification must **execute**, not lint. The headline catch is a concept whose links all resolve and whose markdown is well-formed, but whose **documented analysis produces the wrong number** when run against the real data (ignores survey weights, or a skip-pattern). A green link-check plus a wrong stat is exactly what Baton catches and a passive RAG ships. If the demo's catches are all "broken link / dead ref," we built a linter and oversold it. The whole point is the *number that is confidently wrong*.

## 2a. Architecture: one repo, a project-local specialist skill (generalize later)

Keep it simple to start: **one repo** (`nhis-okf-compiler`), with the domain logic as a **project-local specialist skill** — not a separate portable repo yet. Specific-first, generalize-later (avoid the premature abstraction that, per the maintainer's own NestJS "I overdid it" lesson, is easy to over-build). The composition story still holds — Baton owns process, the skill owns the stats; only the "portable across health datasets" claim is *deferred* until diabetes earns it.

- **Baton core (existing repo)** — orchestrator loop + skill-creator. Owns process, the gated loop, execution-grounded verification, the audit trail. Stays domain-agnostic.
- **`nhis-okf-compiler` (this repo)** — contains:
  - `.claude/skills/data-science/SKILL.md` — the "epidemiological data engineer -> OKF" skill, authored via **skill-creator**, scoped to this project for now (extract to a portable skill later if NHANES/BRFSS reuse materializes).
  - `raw_codebooks/` — the target NHIS Sample Adult codebooks / layout files.
  - `.okf/variables/` — the compiled, verified knowledge base: `DIBEV_A.md` (ever told had diabetes), `DIBAGE_A.md` (age diagnosed), `INSLN_A.md` (currently taking insulin), plus a master `log.md`.

The diabetes variables carry the exact defect class to catch:
- **Skip-pattern / universe.** The insulin item (`DIBINS_A` in the NHIS 2023 file; `INSLN_A` in older years) is a skip-pattern question — empirically asked of adults with diagnosed diabetes *or* prediabetes (`(DIBEV_A == 1) | (PREDIB_A == 1)`), not the whole sample. A naive "% taking insulin" over the whole sample is badly **deflated** (most adults were never asked, so they read as non-users) — it must be "% among diagnosed adults" (`DIBEV_A == 1`), survey-weighted. Built result: naive 3.66% vs correct 31.96%.
- **Redesign rename.** The 2019 NHIS redesign renamed `DIBEV` (Condition module) to `DIBEV_A` (Sample Adult core); a longitudinal join that ignores the rename produces a broken trend.

**The data-science skill's verification gates must EXECUTE, not lint.** Link-auditing (do cross-refs resolve) and universe-documentation are cheap pre-checks a script owns. The gate that earns Baton's keep **runs the documented analysis against the real microdata with proper survey weights and confirms the number** — catching the inflated insulin prevalence, or a trend broken by the rename. A clean-linking concept with a wrong number is the whole point.

## 3. What Baton builds (the loop)

- **discovery** — parse NHIS data dictionaries / codebooks / layout files into OKF concepts (`type: variable_definition`, survey-logic rules, skip-patterns), cross-linked, with `log.md` change history across survey years.
- **plan / implement** — the OKF bundle + a RAG/vector index over it + a query/chat interface. Domain work (weighting, skip-pattern handling) routed to the data-science skill.
- **verify (the point)** — for each analytical concept, **run the documented query against the real NHIS microdata** with proper survey weighting and confirm the result matches the claim; cold-read adversarial brief. Catch the structurally-valid-but-wrong stat.
- **audit** — a `RunRecord` plus the OKF `log.md`: every concept's verification is on the record.

## 4. Safety scoping (non-negotiable)

A tool to explore **public, de-identified, aggregate** survey data — *not* medical or clinical advice. No individual-level inference, no health recommendations, every figure carries its survey-weighted basis and source. State this in the product copy and in the chatbot's own framing.

## 5. Lean slice first

Do not compile all of NHIS. One **survey year** (e.g. NHIS 2023), one **health topic** (e.g. diabetes or hypertension), a handful of variables, and **one** verified analysis (a weighted prevalence). Prove the loop end to end — compile -> execution-verify catches a wrong stat -> grounded answer cites the verified concept — on that slice before scaling years/topics. Same discipline as every Baton dogfood.

## 6. Open decisions

- **Topic: decided — diabetes.** Survey year for the lean slice: a recent post-2019-redesign year (verify the latest NHIS Sample Adult public-use file available, e.g. 2022 or 2023). The cross-year redesign catch (`DIBEV` -> `DIBEV_A`) needs 2018 + a post-redesign year and is a later expansion.
- **Data-science skill: decided — built via skill-creator, kept project-local for now** ("epidemiological data engineer -> OKF"), with **execution gates** that compute survey-weighted statistics. Lives in this repo's `.claude/skills/`, not Baton core and not a separate portable repo yet; extract/generalize later if reuse materializes.
- RAG/vector stack: local embeddings + which vector store; how OKF concepts chunk into the index.
- Run venue: local vs headless on AWS (ties to the earlier "online mode on AWS" thread).
- OKF v0.1 spec fidelity: how strictly to follow the published spec; pin the version.

## 7. Relationships

- **Feeds the study.** This real build can be *seeded* afterward and reused as a realistic fixture for [[review-discipline-eval]] (the build-then-seed bridge).
- **Formative for Baton.** A data-science-domain dogfood: where does Baton's loop help or struggle outside its usual code-change comfort zone? Improve from it, and keep accumulating field evidence.
