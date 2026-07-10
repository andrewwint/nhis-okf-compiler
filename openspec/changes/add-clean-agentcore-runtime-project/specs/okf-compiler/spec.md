# okf-compiler delta: clean AgentCore runtime project (CodeZip, retrieval-only)

## ADDED Requirements

### Requirement: Retrieval-only runtime mode
The agent SHALL support a retrieval-only mode in which only the verified-bundle retrieval tool
is registered, and the retrieval path SHALL NOT require pandas. The full local agent (retrieval
+ subpopulation + groupby) SHALL be unchanged.

#### Scenario: Retrieval-only agent excludes the compute tools
- **WHEN** the runtime tool mode is retrieval-only
- **THEN** the built agent registers only the verified-bundle retrieval tool
- **AND** importing that path does not import pandas

### Requirement: Overridable bundle location
The verified-bundle directory SHALL be resolvable via `NHIS_OKF_DIR`, defaulting to the
repo-relative `.okf/`, so a packaged runtime can read a bundled copy.

#### Scenario: Override redirects retrieval
- **WHEN** `NHIS_OKF_DIR` is set to an alternate directory
- **THEN** retrieval reads the bundle from that directory
- **AND** with it unset, behavior is unchanged

### Requirement: AgentCore runtime project reuses the source agent
The deploy tree SHALL contain an AgentCore CLI runtime project whose entrypoint imports the
`nhis_okf` agent rather than reimplementing it, packaged retrieval-only for CodeZip.

#### Scenario: The runtime entrypoint is a thin wrapper
- **WHEN** the runtime project is packaged
- **THEN** its entrypoint re-exports the source agent app in retrieval-only mode
- **AND** no parallel agent implementation is introduced
