"""Concepts: the documented analytical claims that get compiled into the OKF bundle.

A concept is what a human analyst (or a passive RAG over the codebook PDFs) would
*write down*: a variable, prose, links, and a headline statistic with a stated method
and a claimed value. The markdown can be perfectly clean and every link can resolve
while the claimed number is still wrong. Catching that is the whole project, and it is
`verify.py`'s job — not this module's.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONCEPTS_DIR = REPO_ROOT / "concepts"


@dataclass
class ClaimMethod:
    """The method a concept *says* it used to produce its number."""

    universe_expr: str | None
    weighted: bool


@dataclass
class Concept:
    id: str
    variable: str
    label: str
    # The denominator the claim's statistic actually targets (registry-correct).
    analytical_universe: str | None
    # Analytical concepts carry a headline statistic; descriptive ones do not.
    statistic: str = ""
    method: ClaimMethod | None = None
    value_pct: float | None = None
    tolerance_pct: float = 0.5
    links: list[str] = field(default_factory=list)
    prose: str = ""
    # A concept may be deliberately seeded as a defect, to demonstrate the catch.
    seeded_defect: bool = False
    source_path: Path | None = None

    @property
    def is_analytical(self) -> bool:
        return self.value_pct is not None


def _parse(doc: dict, source: Path | None = None) -> Concept:
    claim = doc.get("claim")
    method = None
    statistic = ""
    value_pct = None
    tolerance_pct = 0.5
    if claim is not None:
        m = claim.get("method", {})
        method = ClaimMethod(
            universe_expr=m.get("universe_expr"),
            weighted=bool(m.get("weighted", True)),
        )
        statistic = claim.get("statistic", "")
        value_pct = float(claim["value_pct"])
        tolerance_pct = float(claim.get("tolerance_pct", 0.5))
    return Concept(
        id=doc["id"],
        variable=doc["variable"],
        label=doc.get("label", ""),
        analytical_universe=doc.get("analytical_universe"),
        statistic=statistic,
        method=method,
        value_pct=value_pct,
        tolerance_pct=tolerance_pct,
        links=list(doc.get("links", [])),
        prose=doc.get("prose", "").strip(),
        seeded_defect=bool(doc.get("seeded_defect", False)),
        source_path=source,
    )


def load_concept(path: str | Path) -> Concept:
    path = Path(path)
    with open(path) as f:
        return _parse(yaml.safe_load(f), source=path)


def load_all(concepts_dir: str | Path = CONCEPTS_DIR) -> list[Concept]:
    concepts_dir = Path(concepts_dir)
    out = [load_concept(p) for p in sorted(concepts_dir.glob("*.yaml"))]
    if not out:
        raise FileNotFoundError(f"no concept YAML files in {concepts_dir}")
    return out
