# okf-compiler delta: OKF-grounded agent row inspection (local)

## ADDED Requirements

### Requirement: OKF-grounded row inspection in the local agent
The local agent SHALL expose a bounded row-inspection tool that returns capped rows for
requested columns with a mandatory raw/unweighted/not-a-population-estimate caveat, and SHALL
attach each returned column's verified OKF concept summary (label, valid codes, universe). It
SHALL register only in the default tool set, never in retrieval mode.

#### Scenario: Rows returned with their OKF column summaries
- **WHEN** a user asks the local agent to inspect rows of verified columns
- **THEN** the agent returns the capped rows with the raw/unweighted caveat and the OKF summary for each column
- **AND** a column without a verified concept is reported as having no OKF summary rather than a fabricated one

#### Scenario: The deployed retrieval-mode agent has no row tool
- **WHEN** the agent is built with `NHIS_RUNTIME_TOOLS=retrieval`
- **THEN** the row-inspection tool is not registered and the retrieval import path does not require pandas

### Requirement: Universe expressions on the agent path are allow-list validated
A universe expression supplied through the agent SHALL be validated against an allow-list
(a column name, a comparison operator, and a number, combined with boolean operators and
parentheses) before evaluation; anything outside the grammar SHALL be rejected, not evaluated.

#### Scenario: A valid universe passes and an injection is rejected
- **WHEN** the universe is `(DIBEV_A == 1) | (SEX_A == 2)`
- **THEN** it validates and is evaluated
- **WHEN** the universe contains an attribute access, call, import, or bare name
- **THEN** it is rejected with a clear error and never evaluated
