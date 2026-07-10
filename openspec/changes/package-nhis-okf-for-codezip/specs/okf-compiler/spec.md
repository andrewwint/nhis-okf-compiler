# okf-compiler delta: CodeZip-packageable runtime

## ADDED Requirements

### Requirement: Retrieval-only base install without pandas
The `nhis_okf` package SHALL install its retrieval path without pandas/pyarrow, which SHALL
be an optional `compute` extra. The runtime agent SHALL import and answer using only the base
install.

#### Scenario: Base install imports the agent
- **WHEN** only the base dependencies are installed (no compute extra)
- **THEN** the retrieval-only agent imports and answers grounded queries
- **AND** a local full install (`[dev]`) still provides pandas for the compute tools and tests

### Requirement: The bundle ships in the built artifact
The verified `.okf/` bundle SHALL be included in the packaged runtime artifact, with no
committed duplicate, and `config.okf_dir()` SHALL fall back to the shipped bundle when the
repo-relative bundle is absent and `NHIS_OKF_DIR` is unset.

#### Scenario: Deployed runtime finds its bundle
- **WHEN** the runtime runs from the package without a repo-relative `.okf/`
- **THEN** it resolves the bundle from the shipped location
