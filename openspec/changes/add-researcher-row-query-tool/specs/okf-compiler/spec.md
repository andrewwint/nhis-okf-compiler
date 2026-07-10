# okf-compiler delta: researcher row-query tool + OKF usage instructions

## ADDED Requirements

### Requirement: Researcher row-level query tool
The system SHALL provide a researcher tool that returns selected columns of the rows
matching an arbitrary universe expression from the public-use microdata. The tool SHALL
require an explicit column list, SHALL bound the number of returned rows, and SHALL label
every result as raw, unweighted, de-identified data that is not a population estimate and
not verified.

#### Scenario: Return selected columns for a subpopulation
- **WHEN** a researcher requests named columns for rows matching a universe expression
- **THEN** the tool returns those columns for the matching rows, up to the row cap
- **AND** it prints a caveat that the records are raw, unweighted, and not verified

#### Scenario: No accidental full dump
- **WHEN** the request omits an explicit column list
- **THEN** the tool errors rather than returning every column

### Requirement: The verified path and deployed agent never return rows
The verified query path and the deployed grounded agent SHALL remain aggregate-only and
SHALL NOT be able to return individual records.

#### Scenario: The agent cannot reach the row tool
- **WHEN** the deployed grounded agent answers a question
- **THEN** it returns only verified aggregate figures and cannot emit individual rows
- **AND** the agent code does not import the row-query tool

### Requirement: OKF documents how to use the row tool
The OKF bundle SHALL include a conformant Reference concept documenting the researcher row
tool, and each analytical variable concept SHALL carry a reproduction section with the exact
weighted (`nhis analyze`) and raw (`nhis rows`) invocations.

#### Scenario: The bundle maps a reader to the tool
- **WHEN** the bundle is compiled
- **THEN** it contains a `references/parquet_query.md` Reference concept with non-empty `type`
- **AND** each analytical concept includes a reproduction section citing its exact query invocations
