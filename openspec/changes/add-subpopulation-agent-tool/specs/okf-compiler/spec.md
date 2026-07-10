# okf-compiler delta: deterministic query-time subpopulation answering

## ADDED Requirements

### Requirement: Deterministic query-time subpopulation answering
The grounded chat agent SHALL be able to answer an ad-hoc subpopulation question by calling
a deterministic tool that computes a survey-weighted aggregate and its design-based
confidence interval for a verified variable over a universe expression. The tool SHALL be
grounded-or-refuse (verified variables only), SHALL return aggregates only (never individual
rows), and SHALL state the survey-weighted basis (universe and weight) with the figure.

#### Scenario: Agent answers an ad-hoc weighted subgroup question
- **WHEN** a user asks the chat for a weighted figure over a subpopulation of a verified variable
- **THEN** the agent computes it deterministically (weighted, correct universe) and returns the estimate with its design-based CI and stated basis

#### Scenario: Refuses an unverified variable
- **WHEN** the requested variable is not backed by a verified concept in the bundle
- **THEN** the tool refuses rather than computing an ungrounded number

#### Scenario: The agent cannot return raw rows
- **WHEN** the agent answers any question
- **THEN** it returns only aggregate figures and cannot reach the raw-row tool
