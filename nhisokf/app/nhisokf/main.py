"""AgentCore entrypoint: the grounded NHIS-OKF chat.

Answers ONLY from the verified OKF bundle vendored in ./okf. Retrieval is pure Python (no
sklearn/numpy) and the few frontmatter fields are parsed with regex (no PyYAML) — so this adds
ZERO dependencies beyond the AgentCore scaffold, which matters on the Python 3.14 runtime where
new wheels are scarce. The agent is grounded-or-refuse: it cites verified concept ids, never
invents a number, and frames every answer as public aggregate survey data — not medical advice.
"""

import math
import re
from collections import Counter
from pathlib import Path

from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from model.load import load_model

app = BedrockAgentCoreApp()
log = app.logger

HERE = Path(__file__).parent
OKF_VARIABLES = HERE / "okf" / "variables"
MAX_QUESTION_CHARS = 600


def _tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def _field(raw: str, name: str, indented: bool = False) -> str | None:
    """Pull a single frontmatter field by regex (avoids a YAML dependency)."""
    prefix = r"^\s+" if indented else r"^"
    m = re.search(prefix + re.escape(name) + r":\s*\"?(.*?)\"?\s*$", raw, re.MULTILINE)
    return m.group(1) if m else None


def _load_bundle() -> list[dict]:
    docs = []
    for p in sorted(OKF_VARIABLES.glob("*.md")):
        raw = p.read_text()
        docs.append(
            {
                "id": _field(raw, "id") or p.stem,
                "title": _field(raw, "title") or p.stem,
                "statistic": _field(raw, "statistic"),
                "value_pct": _field(raw, "value_pct"),
                "detail": _field(raw, "detail", indented=True),
                "tf": Counter(_tokens(raw)),
            }
        )
    return docs


_DOCS = _load_bundle()


def _cosine(q: Counter, d: Counter) -> float:
    common = set(q) & set(d)
    if not common:
        return 0.0
    dot = sum(q[t] * d[t] for t in common)
    nq = math.sqrt(sum(v * v for v in q.values()))
    nd = math.sqrt(sum(v * v for v in d.values()))
    return dot / (nq * nd) if nq and nd else 0.0


@tool
def search_verified_okf(query: str) -> str:
    """Search the verified NHIS OKF bundle. Returns matching concepts with their
    survey-weighted figures and 95% confidence intervals, or NO_VERIFIED_CONCEPTS_FOUND."""
    qtf = Counter(_tokens(query))
    scored = sorted(((d, _cosine(qtf, d["tf"])) for d in _DOCS), key=lambda x: x[1], reverse=True)
    hits = [d for d, s in scored if s > 0][:3]
    if not hits:
        return "NO_VERIFIED_CONCEPTS_FOUND"
    blocks = []
    for d in hits:
        line = f"[{d['id']}] {d['title']}"
        if d["statistic"] and d["value_pct"]:
            line += f"\n  {d['statistic']}: {d['value_pct']}%"
            if d["detail"]:
                line += f" ({d['detail']})"
        blocks.append(line)
    return "\n\n".join(blocks)


GROUNDED_PROMPT = """You answer questions about U.S. health survey statistics using ONLY the
verified NHIS concepts returned by the search_verified_okf tool.

- Always call search_verified_okf first. Use ONLY the figures it returns; quote the exact
  survey-weighted percentage and its 95% CI, and cite the concept id in brackets, e.g. [DIBEV_A].
- If it returns NO_VERIFIED_CONCEPTS_FOUND, say plainly that you cannot answer from the verified
  bundle. Do NOT invent or estimate a number, and do NOT use outside knowledge for figures.
- These are public, aggregate survey estimates. Not medical advice; make no individual-level
  inference. Be concise and state the survey-weighted basis (the universe) with any figure."""


_agent = None


def _get_agent() -> Agent:
    global _agent
    if _agent is None:
        _agent = Agent(
            model=load_model(),
            system_prompt=GROUNDED_PROMPT,
            tools=[search_verified_okf],
        )
    return _agent


@app.entrypoint
async def invoke(payload, context):
    question = (payload.get("question") or payload.get("prompt") or "").strip()
    if not question:
        yield "Please provide a question."
        return
    if len(question) > MAX_QUESTION_CHARS:
        yield f"Question too long (limit {MAX_QUESTION_CHARS} characters)."
        return
    log.info("OKF query: %s", question)
    async for event in _get_agent().stream_async(question):
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]


if __name__ == "__main__":
    app.run()
