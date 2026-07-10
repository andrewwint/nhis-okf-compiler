# okf-compiler delta: body measures + cross-year encoding-compatibility check

## ADDED Requirements

### Requirement: Whole-sample continuous body-measure concepts
The system SHALL verify weighted means for whole-sample continuous body-measure variables
(`WEIGHTLBTC_A`, `HEIGHTTC_A`), excluding their non-substantive top-codes, using the same
execution-grounded comparison against the registry-correct computation.

#### Scenario: Weighted mean weight is verified
- **WHEN** a concept claims the survey-weighted mean weight over the adult sample
- **THEN** the system recomputes it (weighted, non-substantive codes 996–999 dropped) and compares within tolerance

#### Scenario: A defect that retains non-substantive top-codes is caught
- **WHEN** a concept computes the mean while retaining the non-substantive top-codes
- **THEN** the inflated mean diverges from the registry-correct value and is caught by execution while the lint passes
- **AND** the concept is quarantined from the bundle

### Requirement: Cross-year encoding-compatibility check
The system SHALL detect a longitudinal trend that joins a variable across years whose
encodings are incompatible (continuous versus categorical, or non-overlapping substantive
value domains), and SHALL fail such a join before comparing values.

#### Scenario: A BMI continuous-to-categorical recode join is caught
- **WHEN** a concept claims a mean-BMI trend joining 2018 `BMI` (continuous, stored ×100) to 2023 `BMICAT_A` (a 1–4 category)
- **THEN** verification detects the incompatible encoding and fails the concept with a scale/units-mismatch diagnosis
- **AND** the concept is quarantined from the bundle

#### Scenario: A compatible rename trend is unaffected
- **WHEN** a valid trend joins the same underlying measure across a pure rename with a consistent encoding
- **THEN** the encoding-compatibility check does not flag it and the existing verification behavior is unchanged
