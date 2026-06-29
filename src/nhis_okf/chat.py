"""Grounded answering over the verified OKF bundle.

Two modes, chosen automatically:

* **Extractive (default, no key needed):** return the retrieved verified concept's
  statistic with its survey-weighted basis and source citation. Fully functional and
  fully grounded — it can only surface numbers that passed verification.

* **Generative (opt-in):** if ANTHROPIC_API_KEY is set (directly or via a local `.env`),
  compose a natural-language answer *from the retrieved verified context only*, with the
  same citation and safety framing. The key lights this up; nothing else changes.

Safety framing is always attached: this explores public, de-identified, aggregate survey
data — it is not medical advice and makes no individual-level inference.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .retrieval import Retriever, Hit

REPO_ROOT = Path(__file__).resolve().parents[2]
SAFETY = (
    "This tool explores public, de-identified, aggregate survey data (CDC NHIS 2023). "
    "It is not medical advice and makes no individual-level inference. Every figure is "
    "survey-weighted and cited to its source variable."
)


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
        body = f"{top.concept.label}: {top.concept.text.splitlines()[0] if top.concept.text else ''}"
    cites = [_citation(h) for h in hits]
    return Answer(
        text=f"{body}\n\nSource: {cites[0]}\n\n{SAFETY}",
        mode="extractive",
        citations=cites,
        hits=hits,
    )


def _generative_answer(query: str, hits: list[Hit]) -> Answer:
    import anthropic  # imported lazily; only needed in generative mode

    context = "\n\n".join(
        f"[{h.concept.id}] {h.concept.label}\n{h.concept.text}" for h in hits
    )
    prompt = (
        "Answer the question using ONLY the verified NHIS concepts below. Quote the "
        "exact survey-weighted figure and cite the concept id. If the concepts do not "
        f"contain the answer, say so. Do not invent numbers.\n\n"
        f"Question: {query}\n\nVerified concepts:\n{context}"
    )
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in msg.content if block.type == "text")
    return Answer(
        text=f"{text}\n\n{SAFETY}",
        mode="generative",
        citations=[_citation(h) for h in hits],
        hits=hits,
    )


def answer(query: str, k: int = 3, retriever: Retriever | None = None) -> Answer:
    _load_dotenv()
    retriever = retriever or Retriever.from_bundle()
    hits = retriever.search(query, k=k)
    if os.environ.get("ANTHROPIC_API_KEY") and hits:
        try:
            return _generative_answer(query, hits)
        except Exception as exc:  # fall back rather than fail the query
            ans = _extractive_answer(query, hits)
            ans.text = f"[generative mode unavailable: {exc}; using extractive]\n\n" + ans.text
            return ans
    return _extractive_answer(query, hits)
