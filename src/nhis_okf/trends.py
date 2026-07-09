"""Cross-year trends and the 2019 redesign-rename catch.

A longitudinal trend is the second marquee defect class: joining years by a single variable
name silently breaks when the 2019 NHIS redesign renamed the variable (e.g. `DIBEV1` in 2018
-> `DIBEV_A` in 2023). The naive trend looks fine — clean markdown, a plausible series — but
the variable does not exist in one of the years, so the join drops a year. Only *executing*
the per-year computation against the real files catches it.

The correct path resolves each year through the registry's `CROSS_YEAR` map (right variable,
right weight, right valid codes per year). The verifier compares a trend concept's claimed
method and values to that correct computation, and flags a single-name join that hits a
renamed (absent) variable.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yaml

from . import registry
from .analysis import DATA_DIR, compute_prevalence, load_table, table_columns, PrevalenceResult

TRENDS_DIR = Path(__file__).resolve().parents[2] / "concepts" / "trends"

PASS = "PASS"
FAIL = "FAIL"


# --- data access (per year) -----------------------------------------------------------

def year_csv(year: int) -> Path:
    return DATA_DIR / registry.YEAR_FILES[year]


def fetch_year(year: int) -> Path:
    """Download + unzip a year's Sample Adult public-use CSV (idempotent)."""
    import urllib.request

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = year_csv(year)
    if csv_path.exists():
        return csv_path
    zip_path = DATA_DIR / f"_nhis_{year}.zip"
    urllib.request.urlretrieve(registry.YEAR_CSV_ZIP[year], zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(DATA_DIR)
    if not csv_path.exists():
        raise RuntimeError(f"expected {csv_path} after unzip; archive layout changed")
    return csv_path


def _columns_for_year(year: int) -> set[str]:
    return table_columns(year_csv(year))


# --- correct (rename-aware) and naive (single-name) trends ----------------------------

def _resolve(canonical: str, year: int):
    return registry.CROSS_YEAR[canonical][year]


def correct_trend(canonical: str, years: list[int]) -> dict[int, PrevalenceResult]:
    """Weighted prevalence per year, each resolved to its correct variable + weight."""
    out: dict[int, PrevalenceResult] = {}
    for y in years:
        var, weight, valid, affirmative = _resolve(canonical, y)
        df = load_table(year_csv(y), columns=[var, weight])
        out[y] = compute_prevalence(
            df, var, universe_expr=None, affirmative_codes=affirmative,
            valid_codes=valid, weighted=True, weight_var=weight,
        )
    return out


@dataclass
class TrendConcept:
    id: str
    canonical: str
    years: list[int]
    title: str
    statistic: str
    # method: either {year: var} (rename-aware) or a single var name for all years.
    per_year_variable: dict[int, str] | None
    single_variable: str | None
    values_pct: dict[int, float]
    tolerance_pct: float
    prose: str = ""
    links: list[str] = field(default_factory=list)
    seeded_defect: bool = False
    source_path: Path | None = None


@dataclass
class TrendVerifyResult:
    concept_id: str
    verdict: str
    lint_ok: bool
    statistic: str = ""
    correct: dict[int, float] = field(default_factory=dict)
    claimed: dict[int, float] = field(default_factory=dict)
    diagnosis: list[str] = field(default_factory=list)
    seeded_defect: bool = False

    @property
    def caught(self) -> bool:
        return self.verdict == FAIL and self.lint_ok


def load_trends(trends_dir: Path = TRENDS_DIR) -> list[TrendConcept]:
    out: list[TrendConcept] = []
    for p in sorted(Path(trends_dir).glob("*.yaml")):
        doc = yaml.safe_load(p.read_text())
        claim = doc["claim"]
        method = claim.get("method", {})
        pyv = method.get("per_year_variable")
        out.append(
            TrendConcept(
                id=doc["id"],
                canonical=doc["canonical"],
                years=[int(y) for y in doc["years"]],
                title=doc.get("title", doc["id"]),
                statistic=claim.get("statistic", ""),
                per_year_variable={int(k): v for k, v in pyv.items()} if pyv else None,
                single_variable=method.get("single_variable"),
                values_pct={int(k): float(v) for k, v in claim.get("values_pct", {}).items()},
                tolerance_pct=float(claim.get("tolerance_pct", 0.3)),
                prose=(doc.get("prose") or "").strip(),
                links=list(doc.get("links", [])),
                seeded_defect=bool(doc.get("seeded_defect", False)),
                source_path=p,
            )
        )
    return out


def verify_trend(concept: TrendConcept) -> TrendVerifyResult:
    lint_ok = bool(concept.prose.strip()) and concept.canonical in registry.CROSS_YEAR
    diagnosis: list[str] = []

    # 1) Rename-gap check: which variable does the claimed method use per year, and does it
    #    actually exist in that year's file?
    for y in concept.years:
        if concept.per_year_variable:
            used = concept.per_year_variable.get(y)
        else:
            used = concept.single_variable
        if used and used not in _columns_for_year(y):
            correct_var = _resolve(concept.canonical, y)[0]
            diagnosis.append(
                f"{y}: variable {used!r} is not in the data — it was renamed in the 2019 "
                f"redesign; the correct {y} variable is {correct_var!r}. A single-name join "
                f"drops {y}, producing a broken trend."
            )

    # 2) Value check against the correct, rename-aware computation.
    correct = correct_trend(concept.canonical, concept.years)
    correct_pct = {y: round(r.value_pct, 2) for y, r in correct.items()}
    for y in concept.years:
        claimed = concept.values_pct.get(y)
        if claimed is None:
            diagnosis.append(f"{y}: no claimed value")
        elif abs(claimed - correct_pct[y]) > concept.tolerance_pct:
            diagnosis.append(
                f"{y}: claimed {claimed}% vs correct {correct_pct[y]}% "
                f"(>{concept.tolerance_pct}pp off)"
            )

    verdict = PASS if not diagnosis else FAIL
    return TrendVerifyResult(
        concept_id=concept.id,
        verdict=verdict,
        lint_ok=lint_ok,
        statistic=concept.statistic,
        correct=correct_pct,
        claimed=concept.values_pct,
        diagnosis=diagnosis,
        seeded_defect=concept.seeded_defect,
    )


def verify_all_trends(trend_list: list[TrendConcept] | None = None) -> list[TrendVerifyResult]:
    return [verify_trend(c) for c in (trend_list or load_trends())]
