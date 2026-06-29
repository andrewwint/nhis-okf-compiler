"""Execution-grounded verification — the reason this project exists.

Two layers, deliberately separated so the contrast is visible:

* `lint_concept` is the cheap pre-check a script owns: is the markdown there, do the
  links resolve? It knows nothing about statistics and will happily pass a concept whose
  headline number is wrong.

* `verify_concept` *executes*. It recomputes the statistic the registry-correct way
  (true universe + mandatory survey weights) and compares it to the concept's claim. A
  concept can pass the lint and fail here — that gap is the whole thesis.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import registry
from .analysis import compute_prevalence, correct_prevalence, PrevalenceResult
from .concepts import Concept

PASS = "PASS"
FAIL = "FAIL"
DESCRIPTIVE = "DESCRIPTIVE"  # documented, no executable statistic


@dataclass
class LintResult:
    ok: bool
    messages: list[str] = field(default_factory=list)


@dataclass
class VerifyResult:
    concept_id: str
    verdict: str
    lint: LintResult
    statistic: str = ""
    claimed_pct: float | None = None
    correct_pct: float | None = None
    delta_pp: float | None = None
    tolerance_pct: float | None = None
    diagnosis: list[str] = field(default_factory=list)
    correct_detail: str = ""
    seeded_defect: bool = False

    @property
    def caught(self) -> bool:
        """True when execution caught a wrong number that the lint did not."""
        return self.verdict == FAIL and self.lint.ok


def lint_concept(concept: Concept, known_ids: set[str]) -> LintResult:
    """Cheap structural checks: prose present, links resolve. No statistics."""
    msgs: list[str] = []
    if not concept.prose.strip():
        msgs.append("empty prose")
    for link in concept.links:
        if link not in known_ids and link not in registry.REGISTRY:
            msgs.append(f"dead link: {link}")
    if concept.variable not in registry.REGISTRY:
        msgs.append(f"unknown variable: {concept.variable}")
    return LintResult(ok=not msgs, messages=msgs)


def _diagnose(concept: Concept, correct: PrevalenceResult) -> list[str]:
    """Explain *why* a claim diverges from the correct computation."""
    out: list[str] = []
    m = concept.method
    if m is None:
        return out
    if not m.weighted:
        out.append(
            "method is UNWEIGHTED; NHIS estimates require survey weights "
            f"({registry.get(concept.variable).weight})"
        )
    correct_universe = (
        concept.analytical_universe
        if concept.analytical_universe is not None
        else registry.get(concept.variable).universe_expr
    )
    if (m.universe_expr or None) != (correct_universe or None):
        out.append(
            f"universe is {m.universe_expr or 'whole sample'!r}; "
            f"correct analytical universe is {correct_universe or 'all adults'!r}"
        )
    return out


def verify_concept(
    df: pd.DataFrame, concept: Concept, known_ids: set[str]
) -> VerifyResult:
    lint = lint_concept(concept, known_ids)

    # Descriptive concept: nothing to execute. Structural documentation only.
    if not concept.is_analytical:
        return VerifyResult(
            concept_id=concept.id,
            verdict=DESCRIPTIVE if lint.ok else FAIL,
            lint=lint,
            seeded_defect=concept.seeded_defect,
        )

    correct = correct_prevalence(
        df, concept.variable, analytical_universe=concept.analytical_universe
    )
    delta = abs(concept.value_pct - correct.value_pct)
    ok = delta <= concept.tolerance_pct
    diagnosis = [] if ok else _diagnose(concept, correct)

    return VerifyResult(
        concept_id=concept.id,
        verdict=PASS if ok else FAIL,
        lint=lint,
        statistic=concept.statistic,
        claimed_pct=concept.value_pct,
        correct_pct=round(correct.value_pct, 2),
        delta_pp=round(delta, 2),
        tolerance_pct=concept.tolerance_pct,
        diagnosis=diagnosis,
        correct_detail=correct.summary(),
        seeded_defect=concept.seeded_defect,
    )


def verify_all(df: pd.DataFrame, concept_list: list[Concept]) -> list[VerifyResult]:
    known = {c.id for c in concept_list} | {c.variable for c in concept_list}
    return [verify_concept(df, c, known) for c in concept_list]
