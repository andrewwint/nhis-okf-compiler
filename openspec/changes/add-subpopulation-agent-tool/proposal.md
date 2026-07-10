# Change: Give the chat agent a deterministic subpopulation tool

## Why

The chat interface (Bedrock AgentCore) is the primary end-user surface. Today the agent can
only look up precomputed verified concepts, so an end-user question about an ad-hoc
subgroup ("insulin use among diabetic women", "mean weight by sex") gets a refusal even
though the engine can answer it correctly. Exposing the deterministic weighted-subpopulation
computation as an agent tool lets the chat answer those questions from an executed, weighted
result — not an LLM-guessed number — while keeping every existing safety guarantee.

## What Changes

- **New internal agent tool `analyze_subpopulation`.** Wraps `analysis.subpopulation_stat`
  behind the Strands agent: given a verified variable, a universe expression, and a statistic
  kind, it returns the survey-weighted aggregate and its design-based CI. It is
  grounded-or-refuse (verified variables only), aggregate-only, and returns no rows. The tool
  is internal — end users interact only with the chat, never the CLI.
- **Prompt update.** The agent is instructed to use `search_verified_okf` for a precomputed
  concept and `analyze_subpopulation` for an ad-hoc weighted subgroup, to state the
  universe/weight basis with every figure, and to refuse rather than guess.
- **Boundary preserved.** The raw-row tool (`parquet_query` / `nhis rows`) remains
  unreachable from the agent; the agent stays aggregate-only. No raw individual records enter
  a chat answer.

## Consistency with the RAG architecture (README)

The README defines the chat as a retrieval RAG whose grounding is "enforced by what exists,
not by prompt instructions" — the agent retrieves verified concepts and cannot reach a
quarantined figure. This change extends that from **grounded-at-compile-time** to also
**grounded-at-query-time**: `analyze_subpopulation` is not an LLM guess but the same
deterministic, registry-correct, weights-mandatory computation the compile-time verifier
runs, restricted to verified variables and returning aggregates only. It therefore cannot
produce the structurally-valid-but-wrong number the project exists to catch. The README and
the architecture diagram are updated to describe the agent's two deterministic tools
(retrieval + query-time execution) rather than a single retrieval tool.

## Impact

- Affected specs: `okf-compiler` (ADDED: deterministic query-time subpopulation answering).
- Affected code: `chat.py` (new tool + prompt), `agentcore_app.py` only if it enumerates
  tools, `tests/` (hermetic, stubbed model), `README.md` + `docs/SAMPLE.md` (describe the
  two-tool agent; keep the CLI framed as internal/researcher, not the end-user surface). No
  change to `analysis.py`.
- Out of scope (deferred): a weighted groupby/cross-tab table tool (next); exposing the CLI
  to end users; any raw-row access from the agent (explicitly rejected).
