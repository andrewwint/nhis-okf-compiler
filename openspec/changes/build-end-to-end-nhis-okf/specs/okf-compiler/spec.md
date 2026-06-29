# okf-compiler delta: end-to-end product

## ADDED Requirements

### Requirement: Distributional and continuous statistics
The system SHALL verify weighted means and weighted quantiles, not only yes/no
prevalence, using the same execution-grounded comparison against the registry-correct
computation.

#### Scenario: Weighted mean age at diagnosis is verified
- **WHEN** a concept claims the weighted mean age at diabetes diagnosis among `DIBEV_A == 1`
- **THEN** the system recomputes it (weighted, non-substantive codes dropped) and compares within tolerance
- **AND** a claim computed unweighted or over the wrong universe is caught

### Requirement: Design-based variance
The system SHALL compute confidence intervals via Taylor linearization using the survey
design variables (`PSTRAT`, `PPSU`), and carry the interval into the OKF concept and the
answer.

#### Scenario: A verified figure carries a survey-correct interval
- **WHEN** an analytical concept is verified
- **THEN** its OKF frontmatter includes a design-based confidence interval, not just a point estimate

### Requirement: Cross-year trend integrity across the 2019 redesign
The system SHALL detect a longitudinal trend that joins a variable across the 2019 NHIS
redesign rename (e.g. `DIBEV` → `DIBEV_A`) without accounting for it.

#### Scenario: A naive cross-year join is caught
- **WHEN** a concept claims a multi-year diabetes trend joining pre- and post-redesign years by a single variable name
- **THEN** verification detects the rename gap and fails the concept with a diagnosis
- **AND** the broken-trend concept is quarantined from the bundle

### Requirement: Codebook ingestion produces draft concepts that still must be verified
The system SHALL parse NHIS data dictionaries / layout files into draft concepts, and
those drafts SHALL pass execution-grounded verification before entering the trusted bundle.

#### Scenario: An auto-parsed concept with an unconfirmed universe is held
- **WHEN** a concept is generated from the codebook with a universe not confirmed against the data
- **THEN** it is not written to the trusted bundle until verification confirms its statistic

### Requirement: Grounded generative answering with refusal
When generative mode is enabled, the system SHALL answer only from retrieved verified
concepts, SHALL cite concept ids, SHALL NOT invent numbers, and SHALL refuse when the
verified bundle does not contain the answer.

#### Scenario: Generative answer refuses outside the bundle
- **WHEN** a user asks something the verified bundle does not cover and a key is configured
- **THEN** the system states it cannot answer from verified concepts rather than fabricating a figure

## MODIFIED Requirements

### Requirement: Grounded retrieval and answering
The system SHALL answer questions only from the verified bundle, attach a source citation
and a survey-weighted basis, attach the not-medical-advice safety framing, and — in
generative mode — refuse rather than fabricate when the bundle lacks the answer.

#### Scenario: A question is answered with a verified figure
- **WHEN** a user asks about insulin use among adults with diabetes
- **THEN** the answer states the verified figure with its survey-weighted basis, confidence interval, and source
- **AND** the answer never serves a quarantined figure
- **AND** the answer includes the not-medical-advice framing
