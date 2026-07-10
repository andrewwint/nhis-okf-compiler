# okf-compiler delta: deterministic weighted groupby table

## ADDED Requirements

### Requirement: Deterministic weighted groupby table
The system SHALL compute, in a single deterministic call, a survey-weighted aggregate and
its design-based confidence interval for each substantive value of a grouping column,
returning a table of per-group cells. It SHALL drop non-substantive group codes, cap the
number of groups, weight every cell, and return aggregates only (never individual rows). The
measured variable SHALL be grounded-or-refuse.

#### Scenario: A by-group weighted table
- **WHEN** a weighted statistic is requested for a verified variable grouped by a categorical column
- **THEN** the system returns one weighted cell per substantive group value, each with its design-based CI and unweighted n

#### Scenario: Group cap prevents a huge table
- **WHEN** the grouping column has more substantive values than the cap
- **THEN** the system errors rather than emitting an unbounded table

#### Scenario: Refuses an unverified measured variable
- **WHEN** the measured variable is not backed by a verified concept
- **THEN** the tool refuses rather than computing an ungrounded table
