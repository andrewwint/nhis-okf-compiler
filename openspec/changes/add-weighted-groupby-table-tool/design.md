## Context

`analyze_subpopulation` answers one weighted subgroup per call. A by-group table currently
requires the LLM to loop and assemble, making the table assembly non-deterministic. This
change adds a single deterministic groupby that returns the whole weighted table.

## Goals / Non-Goals

- Goals: one deterministic call → a weighted table (each cell + design-based CI); exposed on
  the CLI and as a local agent tool; aggregate-only; grounded-or-refuse.
- Non-Goals: raw-row tables; two-way cross-tabs; the AgentCore runtime port (separate).

## Decisions

- **Reuse the verified compute per cell.** Each group cell is the same registry-correct,
  weighted `subpopulation_stat` over `group == value` (combined with any `extra_universe`),
  so a cell can't drift from what `nhis analyze` / the agent tool already return.
- **Drop non-substantive group codes; cap the group count.** A grouping column's 7/9-type
  codes are excluded so groups are meaningful, and the number of groups is capped so a
  mistaken grouping on a continuous column can't produce a huge table.
- **Aggregate-only, same boundary.** The tool returns aggregate cells; it never touches the
  raw-row path. The agent-boundary test continues to hold.
- **Grounded-or-refuse on the measured variable.** The measured `variable` must be verified
  (same allow-list); the grouping column only partitions and may be any loaded categorical.

## Risks / Trade-offs

- Grouping on a near-continuous column → the group cap errors rather than emitting a giant
  table; document that groupby is for categoricals.
- Small groups → wide CIs / singleton-stratum variance; the design-CI machinery already
  handles singleton strata, and the per-cell n is reported so thin cells are visible.

## Migration Plan

Additive: new function, an optional `--groupby` flag, a new agent tool. Existing
`analyze_subpopulation`, retrieval, the bundle, and the raw-row boundary are unchanged.

## Open Questions

- Whether the deployed (Path B) runtime port reuses `groupby_table` directly or a slimmed
  copy — decided in the separate deploy change after the dependency-feasibility assessment.
