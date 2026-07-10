## Context

The chat (AgentCore) is the only end-user surface. Today it is retrieval-only over the
verified bundle (README), so ad-hoc subgroup questions get a refusal even though the engine
can answer them correctly. This change adds a second, deterministic agent tool.

## Goals / Non-Goals

- Goals: the chat answers ad-hoc verified-variable subgroup questions with a weighted
  estimate + design-based CI, computed deterministically at query time; the safety boundary
  (aggregate-only, no raw rows) is preserved and the README reflects the new architecture.
- Non-Goals: a groupby/table tool (next change); exposing the CLI to end users; any raw-row
  access from the agent.

## Decisions

- **Grounded-at-query-time is still grounded.** The retrieval tool grounds on files that
  exist (compile-time verification). The new tool grounds on the deterministic,
  registry-correct computation — weights mandatory, correct universe, drop non-substantive
  codes — the same method the verifier uses. It is not an LLM-guessed number, so it cannot
  produce the structurally-valid-but-wrong figure the project catches. The README's
  "grounding by absence" becomes "grounding by absence (retrieval) + deterministic execution
  (query-time)".
- **Grounded-or-refuse gates the new tool too.** It answers only for variables backed by a
  verified concept (the same allow-list the CLI uses), so the agent cannot compute over an
  unverified variable. An unverified variable or an empty universe returns a refusal, not a
  number.
- **Two tools, clear division.** `search_verified_okf` for a precomputed concept and its
  prose/CI; `analyze_subpopulation` for an ad-hoc weighted subgroup. The prompt tells the
  agent which to use and to state the universe/weight basis with every figure.
- **The raw-row tool is still not an agent tool.** The existing boundary (chat/agentcore do
  not import `parquet_query`) is retained and tested. Query-time compute returns aggregates;
  raw records remain a separate researcher CLI.

## Risks / Trade-offs

- A runtime figure is not in `log.md`'s compile-time audit trail → it is still deterministic
  and reproducible from the stated universe/weight, and the tool records the same basis with
  every answer; the audit story shifts from "every served number is a compiled file" to
  "every served number is either a compiled file or a deterministic query with its basis".
- Prompt could mis-route (call analyze when retrieval suffices, or vice versa) → both tools
  are grounded/deterministic, so a mis-route degrades helpfulness, not correctness; covered
  by hermetic tests.

## Migration Plan

Additive: a new tool + prompt + doc updates. The retrieval tool, the verified bundle, the
CLI, and the raw-row boundary are unchanged.

## Open Questions

- Whether to also let retrieval results carry a `# Reproduce` hint so the agent can offer the
  exact query — deferred; not required for answering.
