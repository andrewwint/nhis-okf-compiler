# Tasks: build the end-to-end NHIS-OKF product

Each task keeps the non-negotiables: verification executes (never lints), weights are
mandatory, safety scope holds. Implement and verify one slice at a time.

## 1. Diabetes module coverage
- [ ] 1.1 Add remaining diabetes variables to `registry.py` (DIBTYPE_A, DIBA1CLAST_A, DIBPILL_A as analytical, DIBAGETC_A as a distribution) with empirically-confirmed universes — DIBPILL_A + DIBAGETC_A landed; DIBTYPE_A + DIBA1CLAST_A still missing
- [x] 1.2 Author concepts + a seeded defect per new analytical variable (DIBPILL_A; DIBAGETC_A distribution)
- [x] 1.3 `nhis verify` + `nhis compile` green; defects quarantined

## 2. Continuous + distributional statistics
- [x] 2.1 Extend `analysis.py` with weighted mean and weighted quantiles (analysis.weighted_mean/weighted_quantile + correct_mean/correct_quantile; implemented in add-parquet-and-subpopulation-query)
- [x] 2.2 Extend `verify.py` to check mean/quantile claims (not just prevalence) (Concept.kind discriminator; verify._verify_continuous)
- [x] 2.3 Tests: age-at-diagnosis weighted mean verified; a wrong mean is caught (test_verify.py: DIBAGETC_A PASS 47.41 years, DIBAGETC_A__naive caught)

## 3. Design-based variance
- [x] 3.1 Add Taylor-linearization SEs/CIs using PSTRAT/PPSU (hand-rolled; samplics rejected as archived + polars-crash; validated DEFF > 1)
- [x] 3.2 Carry CI into the OKF frontmatter and the answer text
- [x] 3.3 Tests: CI computed; a claim whose point estimate is right but implausibly precise is flagged (DIBEV_A__tightci)

## 4. Multi-year + the redesign-rename defect
- [x] 4.1 `nhis fetch` supports a year argument; load NHIS 2018 + a post-redesign year (YEAR_FILES: 2018 + 2023; trends.fetch_year)
- [x] 4.2 Add the DIBEV → DIBEV_A rename map to the registry (DIBEV1 → DIBEV_A cross-year resolution)
- [x] 4.3 Implement the cross-year trend check; seed a defect that joins across the rename naively (trends.verify_trend; TREND_diabetes_2018_2023 + __naive)
- [x] 4.4 Verify the broken-trend defect is caught and quarantined (test_trends.py)

## 5. Codebook ingestion (discovery)
- [ ] 5.1 `ingest_codebook.py`: parse NHIS layout/dictionary files into draft concepts
- [ ] 5.2 Draft concepts still pass through verification before entering the bundle
- [ ] 5.3 Tests: a parsed concept with an unconfirmed universe is held until verified

## 6. Second condition (hypertension)
- [x] 6.1 Add hypertension variables + universes; author concepts + seeded defect (HYPEV_A, HYPMED_A + HYPMED_A__naive)
- [x] 6.2 Confirm the pattern generalizes with no engine changes (test_hypertension.py)

## 7. Generative answering on Strands + AgentCore
- [x] 7.1 Strands agent with an OKF-retrieval tool; grounded-or-refuse; cite verified ids (validated live, Anthropic + Bedrock)
- [x] 7.2 AgentCore entrypoint (`BedrockAgentCoreApp`) wrapping the agent
- [x] 7.3 Hermetic tests (tool grounding, refusal-is-agent's-job, model selection)
- [ ] 7.4 Deploy via CDK / `agentcore` (AWS, account-touching — gated)
- [ ] 7.5 Conversation memory (AgentCore Memory) for multi-turn

## 8. Eval + packaging
- [ ] 8.1 `evals/`: a seeded-defect set measuring catch-rate per defect class
- [ ] 8.2 Reproducible pipeline doc; CI runs verify + tests
- [ ] 8.3 Record results as a build-then-seed fixture for the review-discipline-eval study

## 9. Safety surface
- [ ] 9.1 Not-medical-advice framing first-class in every answer + any UI
- [ ] 9.2 Document the aggregate-only data boundary in README and product copy
