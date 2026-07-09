# okf-compiler delta: parquet storage layer + subpopulation query

## ADDED Requirements

### Requirement: Parquet columnar storage with CSV fallback
The system SHALL keep the CDC-shipped CSV as the fetched source of truth and MAY
materialize a Parquet twin next to each `data/*.csv`. Data loaders SHALL prefer the Parquet
twin when present and SHALL fall back to the CSV otherwise, and both paths SHALL produce
identical estimates.

#### Scenario: Parquet is preferred when present
- **WHEN** a Parquet twin exists next to a data CSV and a computation loads the microdata
- **THEN** the loader reads the Parquet file with column projection pushed down
- **AND** the resulting estimate equals the estimate computed from the CSV

#### Scenario: CSV fallback when no Parquet exists
- **WHEN** no Parquet twin is present
- **THEN** the loader reads the CSV as before with no change in behavior

#### Scenario: Missing-column projection does not error
- **WHEN** requested columns include names absent from a given year's file
- **THEN** the loader projects only the columns that exist rather than raising

### Requirement: Survey-weighted subpopulation query
The system SHALL provide a query that takes an arbitrary universe expression and a
statistic kind (prevalence, mean, or quantile) and returns only a survey-weighted aggregate
with its design-based confidence interval. The query SHALL be grounded-or-refuse and SHALL
NOT return raw individual records.

#### Scenario: Ad-hoc weighted estimate for a subpopulation
- **WHEN** a user requests a statistic for a verified variable within an arbitrary universe expression
- **THEN** the system returns the survey-weighted aggregate and its design-based confidence interval
- **AND** it does not emit any individual-level rows

#### Scenario: Refusal for an unverified variable
- **WHEN** the requested variable is not backed by a verified concept in the compiled bundle
- **THEN** the system refuses rather than returning an ungrounded number
