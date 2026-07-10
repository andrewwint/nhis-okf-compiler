# okf-compiler delta: two-tool, injection-hardened deploy aligned to the article

## ADDED Requirements

### Requirement: The deployed agent exposes exactly two aggregate tools
The deployed AgentCore agent SHALL advertise exactly two tools, matching the article: a
retrieval tool (`search_verified_okf`) that answers from a precomputed verified concept, and a
survey-weighted aggregate computation tool (`analyze_subpopulation`) that returns a percentage
with a design-based confidence interval for an ad-hoc subgroup. Both tools SHALL return
**aggregate values only** — never raw individual survey rows — and `analyze_subpopulation`
SHALL be restricted to verified variables, refusing rather than guessing for anything else.

#### Scenario: Retrieval answers a precomputed concept
- **WHEN** the deployed agent is asked a question a verified concept carries (insulin use among
  diagnosed adults)
- **THEN** it returns the precomputed survey-weighted figure with its concept id and refuses a
  question the bundle does not contain

#### Scenario: Ad-hoc subgroup is computed deterministically
- **WHEN** the agent is asked for a weighted subgroup no concept precomputes (insulin use among
  women with diagnosed diabetes)
- **THEN** `analyze_subpopulation` computes the survey-weighted percentage with a design-based CI
  over the verified variable, returns an aggregate cell (never rows), and refuses for an
  unverified variable

### Requirement: Agent-supplied universes in the deploy are allow-list validated
A universe expression supplied through the deployed compute tool SHALL pass an allow-list
validator — a column name, a comparison operator, and a number, combined only with `&`, `|`,
and parentheses over known columns — before it reaches `df.eval`. Anything outside that grammar
SHALL be rejected and never evaluated. This is the mitigation for the
`injection-sink@universe-eval` seam, which is present in the deployed artifact because the
deployed compute tool passes an agent-composed universe to `df.eval`.

#### Scenario: A valid universe computes and an injection is rejected
- **WHEN** the universe is `DIBEV_A == 1 & SEX_A == 2`
- **THEN** it validates and the weighted subgroup is computed
- **WHEN** the universe contains an attribute access, call, import, string literal, or bare name
- **THEN** it is rejected with a clear error and never reaches `df.eval`

#### Scenario: Raw rows never ship to the deploy
- **WHEN** the deployed bundle is loaded
- **THEN** no row-returning tool is registered and the raw-row module (`parquet_query`) is not
  vendored — raw-row inspection remains a local-only capability
