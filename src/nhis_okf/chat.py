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
from pathlib import Path
from typing import Any

from . import config
from .retrieval import Retriever, Hit

REPO_ROOT = Path(__file__).resolve().parents[2]
SAFETY = (
    "This tool explores public, de-identified, aggregate survey data (CDC NHIS 2023). "
    "It is not medical advice and makes no individual-level inference. Every figure is "
    "survey-weighted and cited to its source variable."
)

OKF_ANALYST_PROMPT = """\
You answer questions about U.S. health survey statistics using ONLY the verified NHIS
concepts returned by the search_verified_okf tool.

Hard rules:
- Always call search_verified_okf first. Use ONLY the figures it returns. Quote the exact
  survey-weighted percentage and cite the concept id in brackets, e.g. [DIBINS_A].
- If the tool returns nothing relevant, say you cannot answer from the verified bundle. Do
  NOT invent or estimate a number, and do not use outside knowledge for figures.
- These are public, aggregate survey estimates. This is not medical advice; make no
  individual-level inference and give no clinical recommendation.
- Be concise and factual. State the survey-weighted basis (the denominator/universe) with
  any figure.
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


def _as_tool():
    """Wrap search_verified_okf as a Strands tool (imported lazily)."""
    from strands import tool

    return tool(search_verified_okf)


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
                model_id=config.anthropic_model_id(), max_tokens=600
            )
        else:
            from strands.models.bedrock import BedrockModel

            model = BedrockModel(
                model_id=config.bedrock_model_id(), region_name=config.aws_region()
            )

    return Agent(model=model, system_prompt=OKF_ANALYST_PROMPT, tools=[_as_tool()])


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
