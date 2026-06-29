"""Compile verified concepts into an Open Knowledge Format (OKF) bundle.

The bundle is verified *by construction*: only concepts that pass execution-grounded
verification are written to `.okf/variables/`. A concept that fails (the seeded defect)
is quarantined — it never enters the trusted knowledge base — and its rejection is
recorded in `.okf/log.md` with the numbers, so the audit trail shows what was caught and
why. That is the difference between this bundle and a passive RAG over the raw codebook.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import registry
from .concepts import Concept, load_all
from .verify import VerifyResult, verify_all, PASS, FAIL, DESCRIPTIVE

REPO_ROOT = Path(__file__).resolve().parents[2]
OKF_DIR = REPO_ROOT / ".okf"
VARIABLES_DIR = OKF_DIR / "variables"
LOG_PATH = OKF_DIR / "log.md"
SOURCE = "NHIS 2023 Sample Adult public-use file (adult23.csv)"


@dataclass
class CompileReport:
    written: list[str]
    quarantined: list[str]
    results: list[VerifyResult]

    @property
    def ok(self) -> bool:
        # A clean compile catches every seeded defect and writes every sound concept.
        for r in self.results:
            if r.seeded_defect and r.verdict != FAIL:
                return False
            if not r.seeded_defect and r.verdict == FAIL:
                return False
        return True


def _yaml_list(items) -> str:
    return "[" + ", ".join(items) + "]" if items else "[]"


def _frontmatter(concept: Concept, r: VerifyResult, ts: str) -> str:
    var = registry.get(concept.variable)
    lines = [
        "---",
        f"id: {concept.id}",
        f"type: {'variable_definition' if not concept.is_analytical else 'analytical_concept'}",
        f'label: "{concept.label}"',
        f"variable: {concept.variable}",
        f'question_universe: "{var.universe_text}"',
    ]
    if concept.analytical_universe:
        lines.append(f'analytical_universe: "{concept.analytical_universe}"')
    lines.append(f"weight: {var.weight}")
    lines.append(f'source: "{SOURCE}"')
    if concept.is_analytical:
        lines += [
            f'statistic: "{concept.statistic}"',
            f"value_pct: {r.correct_pct}",
        ]
    lines += [
        "verification:",
        f"  verdict: {r.verdict}",
        "  method: execution-grounded",
    ]
    if concept.is_analytical:
        lines += [
            f"  correct_pct: {r.correct_pct}",
            f"  claimed_pct: {r.claimed_pct}",
            f"  delta_pp: {r.delta_pp}",
            f"  detail: \"{r.correct_detail}\"",
        ]
    lines += [
        f"  verified_at: {ts}",
        f"links: {_yaml_list(concept.links)}",
        "---",
    ]
    return "\n".join(lines)


def _body(concept: Concept, r: VerifyResult) -> str:
    parts = [f"# {concept.label}", "", concept.prose, ""]
    if concept.is_analytical:
        parts += [
            "## Verified statistic",
            "",
            f"**{concept.statistic}: {r.correct_pct}%**",
            "",
            f"- Basis: {r.correct_detail}",
            f"- Verification: executed against {SOURCE}; verdict **{r.verdict}**.",
            "",
        ]
    if concept.links:
        parts.append("## Related")
        parts += [f"- [{l}](./{l}.md)" for l in concept.links]
        parts.append("")
    return "\n".join(parts)


def render_concept(concept: Concept, r: VerifyResult, ts: str) -> str:
    return _frontmatter(concept, r, ts) + "\n\n" + _body(concept, r)


def _write_log(report_results: list[VerifyResult], ts: str) -> None:
    lines = [
        "# OKF audit log",
        "",
        f"Compiled from {SOURCE}.",
        f"Last run: {ts}",
        "",
        "Every concept is verified by *executing* its analysis against the real",
        "microdata with proper survey weights — not by checking links. Quarantined",
        "concepts failed that check and were kept out of the trusted bundle.",
        "",
        "| concept | verdict | claimed | correct | delta (pp) | note |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in report_results:
        claimed = "—" if r.claimed_pct is None else f"{r.claimed_pct}"
        correct = "—" if r.correct_pct is None else f"{r.correct_pct}"
        delta = "—" if r.delta_pp is None else f"{r.delta_pp}"
        note = ""
        if r.verdict == FAIL:
            note = "; ".join(r.diagnosis) or "claim does not match executed result"
            if r.caught:
                note = "QUARANTINED — lint passed, execution caught it: " + note
        elif r.verdict == DESCRIPTIVE:
            note = "documented (no executable statistic)"
        lines.append(
            f"| {r.concept_id} | {r.verdict} | {claimed} | {correct} | {delta} | {note} |"
        )
    lines.append("")
    LOG_PATH.write_text("\n".join(lines))


def compile_bundle(
    df: pd.DataFrame, concept_list: list[Concept] | None = None
) -> CompileReport:
    concept_list = concept_list or load_all()
    results = verify_all(df, concept_list)
    by_id = {c.id: c for c in concept_list}

    VARIABLES_DIR.mkdir(parents=True, exist_ok=True)
    # Start clean so quarantined concepts never linger from a previous run.
    for old in VARIABLES_DIR.glob("*.md"):
        old.unlink()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    written, quarantined = [], []
    for r in results:
        concept = by_id[r.concept_id]
        if r.verdict == FAIL:
            quarantined.append(r.concept_id)
            continue
        (VARIABLES_DIR / f"{concept.id}.md").write_text(render_concept(concept, r, ts))
        written.append(concept.id)

    _write_log(results, ts)
    return CompileReport(written=written, quarantined=quarantined, results=results)
