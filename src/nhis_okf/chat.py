"""Grounded answering over the verified OKF bundle.

Three layers, chosen automatically:

* **Extractive (default, no key, no agent deps):** return the retrieved verified concept's
  statistic with its survey-weighted basis and source citation. Fully grounded — it can
  only surface numbers that passed verification.

* **Strands agent (opt-in, local testing):** a Strands `Agent` with a `search_verified_okf`
  tool. When `ANTHROPIC_API_KEY` is set, it runs against the Anthropic API; the deploy
  target is the same agent on Bedrock (see `config.bedrock_model_id`). The agent is
  grounded-or-refuse and may cite only verified concepts.

* **AgentCore (deploy):** the same agent wrapped in `BedrockAgentCoreApp` — see
  `agentcore_app.py`.

The model is injectable so tests never touch the network. Safety framing — public,
aggregate, not medical advice — is always attached.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import config, registry
from .retrieval import Retriever, Hit, verified_variables

REPO_ROOT = Path(__file__).resolve().parents[2]
SAFETY = (
    "This tool explores public, de-identified, aggregate survey data (CDC NHIS 2023). "
    "It is not medical advice and makes no individual-level inference. Every figure is "
    "survey-weighted and cited to its source variable. (Raw, unweighted public-use rows "
    "are available only through a separate, explicitly caveated LOCAL row-inspection tool — "
    "never in the deployed aggregate-only agent — and such rows are not population "
    "estimates.)"
)

# Per-invocation cost guardrails (the public endpoint has no auth — these bound spend).
# Output is hard-capped at the model; input is length-limited; one grounded answer per call
# (no multi-turn accumulation). With a public no-auth endpoint these + an AWS budget alarm
# are the only things between the endpoint and a runaway bill, so keep them tight.
MAX_OUTPUT_TOKENS = 600
MAX_QUESTION_CHARS = 600

OKF_ANALYST_PROMPT = """\
You answer questions about U.S. health survey statistics using ONLY the verified,
deterministic tools below. Never use outside knowledge for a figure.

Your tools:
- search_verified_okf(query): retrieval over the verified OKF bundle. Use it for a
  precomputed concept the bundle already carries (e.g. insulin use among diagnosed
  adults). Quote the exact survey-weighted percentage and cite the concept id in brackets,
  e.g. [DIBINS_A].
- analyze_subpopulation(variable, universe, stat, q): a deterministic, survey-weighted
  computation with a design-based confidence interval. Use it for an ad-hoc weighted
  SUBGROUP a concept does not already carry (e.g. a figure restricted to women, or a mean
  age at diagnosis for a subset). `variable` must be a verified variable; `universe` is a
  pandas row filter over the microdata, e.g. "DIBEV_A == 1 & SEX_A == 2". `stat` is one of
  prevalence | mean | quantile. It returns only an aggregate estimate and its CI.
- groupby_table(variable, groupby, stat, universe, q): a deterministic, survey-weighted
  TABLE — one aggregate cell (estimate + design-based CI) per substantive value of a
  grouping column. Use it for a "by <group>" question (e.g. "insulin use by sex", "mean
  weight by BMI category"). `variable` must be a verified variable; `groupby` is the
  categorical column to tabulate by (e.g. "SEX_A"); `universe` is an optional filter
  combined with each group (e.g. "DIBEV_A == 1"). It returns only aggregate cells, never
  rows.
- inspect_rows(columns, universe, limit): a few RAW, UNWEIGHTED public-use microdata rows
  for the requested `columns`, plus each returned column's verified OKF summary (label,
  valid codes, universe/skip-pattern). Use it ONLY for "show me some rows / what does this
  column mean / what are the codes for X" — an inspection or a column-meaning question.
  `columns` is a short list (e.g. ["DIBEV_A","DIBINS_A"]); `universe` is a row filter of
  the form COLUMN <op> NUMBER joined by & | ( ) (e.g. "DIBEV_A == 1"); `limit` is small.

Hard rules:
- For any FIGURE (a percentage, count, mean, rate, "how many/what share"): use ONLY
  search_verified_okf (precomputed concept), groupby_table (a "by <group>" table), or
  analyze_subpopulation (one ad-hoc weighted subgroup). NEVER quote a number computed or
  read off raw rows — inspect_rows is for inspection and column meaning, not for figures.
- Use inspect_rows for "show me rows" or "what does this column mean / what are its codes."
  When you show rows, ALWAYS surface the raw/unweighted caveat the tool returns verbatim,
  and explain the columns using the OKF summary the tool attaches — never guess a column's
  meaning. A column reported as having no OKF summary must be described as such.
- If a tool returns nothing relevant or a REFUSED message, say you cannot answer that from
  the verified bundle. Do NOT invent, estimate, or guess a number.
- ALWAYS state the survey-weighted basis (the universe/denominator and that it is
  weighted) with any figure, and report the confidence interval when the tool gives one.
- These are public, aggregate survey estimates. This is not medical advice; make no
  individual-level inference and give no clinical recommendation. Raw rows, when shown, are
  unweighted individual public-use records — they are NOT population estimates.
- Be concise and factual.
"""


def _load_dotenv(path: Path = REPO_ROOT / ".env") -> None:
    """Minimal .env loader so a dropped-in key is picked up without extra deps."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


@dataclass
class Answer:
    text: str
    mode: str  # "extractive" | "generative"
    citations: list[str] = field(default_factory=list)
    hits: list[Hit] = field(default_factory=list)


def _citation(hit: Hit) -> str:
    fm = hit.concept.frontmatter
    src = fm.get("source", "NHIS 2023 Sample Adult")
    return f"{hit.concept.id} ({src})"


# --- Strands tool: the agent's only window onto the data is the verified bundle ----------

def _format_hits(hits: list[Hit]) -> str:
    if not hits:
        return "NO_VERIFIED_CONCEPTS_FOUND"
    blocks = []
    for h in hits:
        fm = h.concept.frontmatter
        stat = fm.get("statistic")
        val = fm.get("value_pct")
        detail = (fm.get("verification") or {}).get("detail", "")
        line = f"[{h.concept.id}] {h.concept.label}"
        if stat and val is not None:
            line += f"\n  {stat}: {val}% ({detail})"
        else:
            line += f"\n  {h.concept.text.splitlines()[0] if h.concept.text else ''}"
        blocks.append(line)
    return "\n\n".join(blocks)


def search_verified_okf(query: str) -> str:
    """Search the verified NHIS OKF bundle and return matching concepts with their
    survey-weighted figures. Returns NO_VERIFIED_CONCEPTS_FOUND if nothing matches."""
    hits = Retriever.from_bundle().search(query, k=3)
    return _format_hits(hits)


# --- OKF column-summary lookup: the agent's GROUNDING for what a raw column means --------

def _format_valid_codes(codes: tuple[int, ...]) -> str:
    """Compact, human-readable rendering of a variable's valid response codes.

    A short categorical set is listed in full; a wide continuous band (e.g. an age range)
    is summarized as its bounds + count so the summary stays a few lines, not a code dump.
    """
    if not codes:
        return "(none recorded)"
    if len(codes) <= 12:
        return ", ".join(str(c) for c in codes)
    return f"{min(codes)}–{max(codes)} ({len(codes)} values)"


def okf_column_summary(column: str) -> str:
    """Return a column's VERIFIED OKF summary — label, valid codes, universe/skip-pattern,
    and notes — sourced from the registry and gated by the compiled bundle.

    A column is "grounded" only if it is backed by a verified concept in the compiled
    bundle (`verified_variables()`); its structured meaning then comes from the ground-truth
    registry the concept was verified against. A column with no verified concept (e.g. a
    grouping column like SEX_A, or an unknown name) returns a clear "no OKF summary" note —
    it NEVER fabricates a meaning.
    """
    verified = verified_variables()
    if column not in verified or column not in registry.REGISTRY:
        return (
            f"[{column}] no OKF summary — {column} is not backed by a verified concept in "
            f"the compiled bundle, so its meaning is not asserted here."
        )
    var = registry.get(column)
    lines = [f"[{column}] {var.label} (verified OKF concept)"]
    lines.append(f"  valid codes: {_format_valid_codes(var.valid_codes)}")
    if var.affirmative_codes:
        aff = ", ".join(str(c) for c in var.affirmative_codes)
        lines.append(f"  affirmative ('yes') code(s): {aff}")
    lines.append(f"  universe (skip-pattern): {var.universe_text}")
    if var.notes:
        lines.append(f"  notes: {var.notes}")
    return "\n".join(lines)


# --- Agent-path universe gate: close the df.eval injection sink (see analysis._mask) -----

def _agent_allowed_columns():
    """The real microdata columns an agent universe may reference (the allow-list source).

    Read from the file schema (cheap, no data load) so identifiers are validated against
    actual columns, not a hardcoded list. Lazily imports `analysis` so retrieval mode stays
    pandas-free — this only runs when a default-mode compute/inspection tool is invoked.
    """
    from . import analysis

    return analysis.table_columns(analysis.DEFAULT_CSV)


def _validate_agent_universe(universe: str | None) -> None:
    """Gate an agent-supplied universe through the allow-list before ANY df.eval.

    Raises ValueError (never evaluates) for anything outside `COLUMN <op> NUMBER` joined by
    `& | ( )` over known columns. This is the `injection-sink@universe-eval` mitigation for
    every agent tool that reaches `analysis`/`parquet_query` (which call `_mask`'s df.eval).
    """
    if not universe:
        return
    from . import analysis

    analysis.validate_universe(universe, _agent_allowed_columns())


@lru_cache(maxsize=1)
def _microdata():
    """The NHIS microdata, loaded once per process for the query-time tool.

    Full table (all columns) so an ad-hoc universe may reference any verified variable and
    the registry's weight/design columns. Prefers the parquet twin, so this is cheap.

    `analysis` (and thus pandas) is imported lazily here so the retrieval-only path — the
    packaged AgentCore runtime — never drags pandas into the CodeZip.
    """
    from . import analysis

    return analysis.load_microdata()


def analyze_subpopulation(
    variable: str, universe: str, stat: str = "prevalence", q: float = 0.5
) -> str:
    """Compute a survey-weighted aggregate + design-based CI for an ad-hoc subpopulation of
    a VERIFIED NHIS variable.

    Use this for a weighted subgroup figure a precomputed concept does not already carry.
    `variable` must be a verified variable; `universe` is a pandas row filter over the
    microdata (e.g. "DIBEV_A == 1 & SEX_A == 2"); `stat` is prevalence | mean | quantile;
    `q` is the quantile probability when stat is quantile. Returns only an aggregate
    estimate and its confidence interval — never individual rows. Returns a message
    beginning with REFUSED for an unverified variable or an empty/undefined subpopulation.
    """
    allowed = verified_variables()
    if variable not in allowed:
        return (
            f"REFUSED: {variable!r} is not backed by a verified concept in the compiled "
            f"bundle, so no grounded figure can be computed. Verified variables: "
            f"{', '.join(sorted(allowed)) or '(none compiled)'}."
        )
    try:
        _validate_agent_universe(universe)
    except ValueError as exc:
        return f"REFUSED: universe not allowed — {exc}."
    from . import analysis

    try:
        res = analysis.subpopulation_stat(
            _microdata(), variable, universe_expr=universe, stat=stat, q=q
        )
    except Exception as exc:
        return f"REFUSED: could not compute a grounded figure — {exc}."
    return res.summary()


def groupby_table(
    variable: str, groupby: str, stat: str = "prevalence",
    universe: str | None = None, q: float = 0.5,
) -> str:
    """Compute a survey-weighted by-group TABLE for a VERIFIED NHIS variable: one aggregate
    cell (estimate + design-based CI) per substantive value of a grouping column.

    Use this for a "by <group>" question (e.g. insulin use by sex, mean weight by BMI
    category) — a single deterministic call returns the whole weighted table. `variable`
    must be a verified variable; `groupby` is a categorical column to tabulate by (e.g.
    "SEX_A"); `stat` is prevalence | mean | quantile; `universe` is an optional pandas row
    filter combined (AND) with each group (e.g. "DIBEV_A == 1" for among-diagnosed); `q` is
    the quantile probability when stat is quantile. Returns only aggregate cells — never
    individual rows. Returns a message beginning with REFUSED for an unverified variable or
    when no table can be computed (e.g. the group cap is exceeded).
    """
    allowed = verified_variables()
    if variable not in allowed:
        return (
            f"REFUSED: {variable!r} is not backed by a verified concept in the compiled "
            f"bundle, so no grounded table can be computed. Verified variables: "
            f"{', '.join(sorted(allowed)) or '(none compiled)'}."
        )
    try:
        _validate_agent_universe(universe)
    except ValueError as exc:
        return f"REFUSED: universe not allowed — {exc}."
    from . import analysis

    try:
        table = analysis.groupby_table(
            _microdata(), variable, groupby, stat=stat, q=q, extra_universe=universe
        )
    except Exception as exc:
        return f"REFUSED: could not compute a grounded table — {exc}."
    return table.summary()


def inspect_rows(
    columns: list[str], universe: str | None = None, limit: int = 10
) -> str:
    """Inspect a few RAW, UNWEIGHTED public-use NHIS rows for the requested `columns`,
    each paired with its verified OKF column summary (LOCAL default mode only).

    Use this for "show me some rows" or "what does this column mean / what are its codes" —
    an inspection or column-meaning question, NEVER for a figure. `columns` is a short list
    (at most 12); `universe` is a row filter of the form COLUMN <op> NUMBER joined by
    `& | ( )` (e.g. "DIBEV_A == 1"); `limit` is small (hard-capped). It returns the
    mandatory raw/unweighted/not-a-population-estimate banner, the capped rows, and the OKF
    summary for each returned column. Raw rows are individual records — they are NOT a
    population estimate and no rate may be read off them; for a weighted figure use
    analyze_subpopulation / groupby_table / search_verified_okf. Returns a message beginning
    with REFUSED for a disallowed universe or an unusable request.

    `analysis`/`parquet_query` (and thus pandas) are imported lazily inside this tool so the
    retrieval-only deployed runtime — which never registers this tool — stays pandas-free.
    """
    # Injection gate FIRST: the agent-composed universe must pass the allow-list before it
    # can reach parquet_query -> analysis._mask -> df.eval (the injection-sink seam).
    try:
        _validate_agent_universe(universe)
    except ValueError as exc:
        return f"REFUSED: universe not allowed — {exc}."
    from . import parquet_query

    try:
        rows = parquet_query.query_rows(columns, universe_expr=universe, limit=limit)
    except Exception as exc:
        return f"REFUSED: could not inspect rows — {exc}."

    effective = min(limit, parquet_query.HARD_MAX_LIMIT)
    parts = [
        parquet_query.ROWS_CAVEAT,
        "",
        rows.to_string(index=False),
        "",
        f"{len(rows)} row(s) shown (limit {effective}, hard max "
        f"{parquet_query.HARD_MAX_LIMIT}).",
        "",
        "OKF column summaries (what each column means, from the verified bundle):",
    ]
    parts.extend(okf_column_summary(c) for c in rows.columns)
    return "\n".join(parts)


def _as_tools():
    """Wrap the agent's deterministic tools as Strands tools (imported lazily).

    Grounded aggregate tools: retrieval over the verified bundle, a deterministic weighted
    subpopulation computation, and a deterministic weighted by-group table — each restricted
    to verified variables and returning aggregates only. In DEFAULT (local) mode a bounded
    `inspect_rows` tool is also registered: it returns capped, caveated RAW rows for
    inspection alongside each column's OKF summary — the one non-aggregate surface, local
    only.

    When `NHIS_RUNTIME_TOOLS == "retrieval"` ONLY the retrieval tool is registered. That is
    the packaged AgentCore deploy mode: it stays aggregate-only and pandas-free (the compute
    and row tools import `analysis`/`parquet_query`/pandas lazily and are simply not wired
    up, so importing this module in retrieval mode drags in no pandas). Any other value
    (including unset) registers the full local tool set.
    """
    from strands import tool

    if os.environ.get("NHIS_RUNTIME_TOOLS") == "retrieval":
        return [tool(search_verified_okf)]
    return [
        tool(search_verified_okf),
        tool(analyze_subpopulation),
        tool(groupby_table),
        tool(inspect_rows),
    ]


def build_chat_agent(model: Any | None = None):
    """Build the Strands grounded-answering agent.

    Model selection when none is injected:
      * ANTHROPIC_API_KEY present -> Anthropic API (local testing)
      * otherwise -> Bedrock (the AgentCore deploy path)
    Tests inject a stub model so no network call occurs.
    """
    from strands import Agent

    if model is None:
        if config.has_anthropic_key():
            from strands.models.anthropic import AnthropicModel

            model = AnthropicModel(
                model_id=config.anthropic_model_id(), max_tokens=MAX_OUTPUT_TOKENS
            )
        else:
            from strands.models.bedrock import BedrockModel

            model = BedrockModel(
                model_id=config.bedrock_model_id(),
                region_name=config.aws_region(),
                max_tokens=MAX_OUTPUT_TOKENS,
            )

    return Agent(model=model, system_prompt=OKF_ANALYST_PROMPT, tools=_as_tools())


# --- Public entry: extractive by default, generative when a model is available ----------

def _extractive_answer(query: str, hits: list[Hit]) -> Answer:
    if not hits:
        return Answer(
            text=f"No verified concept matches that question.\n\n{SAFETY}",
            mode="extractive",
        )
    top = hits[0]
    fm = top.concept.frontmatter
    stat = fm.get("statistic")
    value = fm.get("value_pct")
    if stat and value is not None:
        body = f"{stat}: {value}%."
        detail = (fm.get("verification") or {}).get("detail")
        if detail:
            body += f" ({detail})"
    else:
        first = top.concept.text.splitlines()[0] if top.concept.text else ""
        body = f"{top.concept.label}: {first}"
    cites = [_citation(h) for h in hits]
    return Answer(
        text=f"{body}\n\nSource: {cites[0]}\n\n{SAFETY}",
        mode="extractive",
        citations=cites,
        hits=hits,
    )


def _generative_answer(query: str, hits: list[Hit], model: Any | None) -> Answer:
    agent = build_chat_agent(model=model)
    result = agent(query)
    text = str(result).strip()
    return Answer(
        text=f"{text}\n\n{SAFETY}",
        mode="generative",
        citations=[_citation(h) for h in hits],
        hits=hits,
    )


def answer(
    query: str,
    k: int = 3,
    retriever: Retriever | None = None,
    *,
    model: Any | None = None,
    generative: bool | None = None,
) -> Answer:
    """Answer a question grounded in the verified bundle.

    `generative` defaults to True when a model is injected or an Anthropic key is present;
    set it False to force the keyless extractive path. The extractive path is always the
    fallback if the agent errors.
    """
    _load_dotenv()
    # Input guardrail: reject over-long questions before any model call (cost cap on a
    # public, unauthenticated endpoint).
    if len(query) > MAX_QUESTION_CHARS:
        return Answer(
            text=(
                f"Question too long (limit {MAX_QUESTION_CHARS} characters). Please ask a "
                f"shorter, specific question.\n\n{SAFETY}"
            ),
            mode="rejected",
        )
    retriever = retriever or Retriever.from_bundle()
    hits = retriever.search(query, k=k)

    if generative is None:
        generative = model is not None or config.has_anthropic_key()

    if generative and hits:
        try:
            return _generative_answer(query, hits, model)
        except Exception as exc:  # never fail the query; fall back to grounded extractive
            ans = _extractive_answer(query, hits)
            ans.text = f"[generative unavailable: {exc}; using extractive]\n\n" + ans.text
            return ans

    return _extractive_answer(query, hits)
