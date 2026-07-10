# okf-compiler delta: one deploy tree, one agent

## MODIFIED Requirements

### Requirement: Grounded generative answering with refusal
When generative mode is enabled, the system SHALL answer only from retrieved verified
concepts, SHALL cite concept ids, SHALL NOT invent numbers, and SHALL refuse when the
verified bundle does not contain the answer. There SHALL be exactly one agent implementation
(`src/nhis_okf`) and one deploy tree (`deploy/`) that runs it; the deployed runtime SHALL NOT
be a separate reimplementation or carry a separately-maintained copy of the bundle.

#### Scenario: Generative answer refuses outside the bundle
- **WHEN** a user asks something the verified bundle does not cover and a key is configured
- **THEN** the system states it cannot answer from verified concepts rather than fabricating a figure

#### Scenario: The deployed agent is the source-of-truth agent
- **WHEN** the deploy tree packages the runtime
- **THEN** it runs `src/nhis_okf/agentcore_app.py` over the canonical `.okf/` bundle
- **AND** there is no parallel agent implementation or duplicate bundle in the repo
