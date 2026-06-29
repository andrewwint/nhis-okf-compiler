# okf-compiler Specification

The verified-OKF-compiler capability, as built in the lean diabetes slice (NHIS 2023).

## Purpose

Compile documented analytical concepts about NHIS variables into an Open Knowledge Format
bundle whose every figure has been verified by *executing* the analysis against the real
microdata with proper survey weights — not by checking links.

## Requirements

### Requirement: Survey-weighted prevalence computation
The system SHALL compute prevalence estimates using the NHIS final annual weight
(`WTFA_A`), excluding non-substantive response codes, within an explicit universe.

#### Scenario: Weighted estimate over a universe
- **WHEN** computing the prevalence of an affirmative response for a variable within a universe
- **THEN** the denominator and numerator are summed over `WTFA_A`, not row counts
- **AND** rows with non-substantive codes (e.g. 7/8/9) are excluded from the denominator

#### Scenario: Diabetes prevalence matches CDC methodology
- **WHEN** computing diagnosed-diabetes prevalence (`DIBEV_A == 1`) over all sample adults
- **THEN** the weighted estimate is ~9.8% (within 0.3 percentage points)

### Requirement: Skip-pattern universe correctness
The system SHALL apply the analytical universe a claim targets, confirmed empirically
against the data, rather than the whole sample or an over-broad question universe.

#### Scenario: Insulin use among diagnosed diabetics
- **WHEN** computing the share currently taking insulin (`DIBINS_A == 1`) among adults with diagnosed diabetes
- **THEN** the denominator is `DIBEV_A == 1` (not the whole sample, not the prediabetes-inclusive question universe)
- **AND** the weighted estimate is ~31.96%

### Requirement: Execution-grounded verification
The system SHALL verify each analytical concept by recomputing the statistic the
registry-correct way and comparing it to the concept's claimed value within a tolerance.
Verification SHALL be independent of the method the concept claims to have used.

#### Scenario: A clean-linking concept with a wrong number is caught
- **WHEN** a concept has well-formed markdown and resolving links but a statistically wrong claimed value
- **THEN** the cheap lint passes
- **AND** execution-grounded verification returns FAIL with the correct value, the delta, and a diagnosis (e.g. unweighted, wrong universe)

#### Scenario: A correct concept passes
- **WHEN** a concept's claimed value matches the registry-correct computation within tolerance
- **THEN** verification returns PASS

### Requirement: Verified-by-construction bundle
The compiler SHALL write only concepts that pass verification to `.okf/variables/`, and
SHALL quarantine failing concepts to `.okf/log.md` with the numbers and diagnosis.

#### Scenario: Seeded defect is quarantined, not published
- **WHEN** compiling a concept set that includes a seeded defect
- **THEN** the defect concept file is absent from `.okf/variables/`
- **AND** its claimed value does not appear anywhere in the trusted bundle
- **AND** the audit log records the rejection and reason

### Requirement: Grounded retrieval and answering
The system SHALL answer questions only from the verified bundle, attach a source citation,
and attach a safety framing that the data is public/aggregate and not medical advice.

#### Scenario: A question is answered with a verified figure
- **WHEN** a user asks about insulin use among adults with diabetes
- **THEN** the answer states the verified figure (~31.96%) with its survey-weighted basis and source
- **AND** the answer never serves a quarantined figure
- **AND** the answer includes the not-medical-advice framing

### Requirement: Local-first operation
The system SHALL run without network access or an API key for compile, verify, and
extractive query. Generative answering SHALL be optional and activated only when an API
key is present.

#### Scenario: Query without an API key
- **WHEN** no `ANTHROPIC_API_KEY` is configured
- **THEN** `query` returns an extractive answer grounded in the verified bundle
