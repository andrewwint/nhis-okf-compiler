"""Survey-weighted analysis engine for NHIS.

This is the statistical core the data-science skill owns. One generic prevalence
function runs *both* a concept's documented method and the registry-correct method, so
the verifier can compare them on equal footing. Survey weighting is applied by default
because unweighted NHIS counts do not estimate the population.
"""

from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import registry

# Resolve data relative to the repo root so the CLI works from anywhere.
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
DEFAULT_CSV = DATA_DIR / "adult23.csv"
NHIS_2023_ADULT_CSV_ZIP = (
    "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NHIS/2023/adult23csv.zip"
)


@dataclass
class PrevalenceResult:
    """The outcome of one prevalence computation."""

    variable: str
    universe_expr: str | None
    weighted: bool
    value_pct: float
    numerator_unweighted: int
    denominator_unweighted: int
    denominator_weighted: float
    weight_var: str | None

    def summary(self) -> str:
        basis = f"weighted by {self.weight_var}" if self.weighted else "UNWEIGHTED"
        uni = self.universe_expr or "all sample adults"
        return (
            f"{self.value_pct:.2f}% ({basis}; universe: {uni}; "
            f"n={self.denominator_unweighted} unweighted)"
        )


def load_microdata(csv_path: str | Path = DEFAULT_CSV, columns=None) -> pd.DataFrame:
    """Load the NHIS Sample Adult CSV, optionally restricting to `columns`."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"{csv_path} not found. Run `nhis fetch` to download the public-use file."
        )
    usecols = (lambda c: c in set(columns)) if columns else None
    return pd.read_csv(csv_path, usecols=usecols, low_memory=False)


def _mask(df: pd.DataFrame, expr: str | None) -> pd.Series:
    """Boolean mask for a universe expression, or all-True when expr is None.

    NOTE (trust boundary): `expr` comes from registry/concept files authored in this
    repo and the tool runs locally, so `df.eval` is safe here. If concepts ever accept
    untrusted input, or this gains a web surface, replace `eval` with a parsed,
    allow-listed predicate — `eval` on untrusted strings is a code-injection vector.
    """
    if expr is None:
        return pd.Series(True, index=df.index)
    return df.eval(expr)


def compute_prevalence(
    df: pd.DataFrame,
    variable: str,
    *,
    universe_expr: str | None,
    affirmative_codes: tuple[int, ...],
    valid_codes: tuple[int, ...],
    weighted: bool = True,
    weight_var: str = registry.SAMPLE_ADULT_WEIGHT,
    denominator: str = "valid",
) -> PrevalenceResult:
    """Prevalence of `affirmative_codes` among a denominator within a universe.

    Every knob is explicit so the same function can express both a correct analysis
    and a flawed one (wrong universe, weighting off, wrong denominator). The verifier
    exploits that.

    `denominator`:
      * "valid" (correct) — only substantive responses count toward the denominator.
      * "all_in_universe" (a classic skip-pattern error) — every row in the universe
        counts, so people who were never asked are silently treated as non-affirmative.
        With universe=None this is the "% of the whole sample" mistake.
    """
    in_universe = _mask(df, universe_expr)
    if denominator == "all_in_universe":
        denom_rows = df[in_universe]
    elif denominator == "valid":
        denom_rows = df[in_universe & df[variable].isin(valid_codes)]
    else:
        raise ValueError(f"unknown denominator mode: {denominator!r}")
    num_rows = denom_rows[denom_rows[variable].isin(affirmative_codes)]

    if weighted:
        w = denom_rows[weight_var]
        denom_w = float(w.sum())
        num_w = float(num_rows[weight_var].sum())
        value = (num_w / denom_w * 100.0) if denom_w else 0.0
    else:
        denom_w = float(len(denom_rows))
        value = (len(num_rows) / denom_w * 100.0) if denom_w else 0.0

    return PrevalenceResult(
        variable=variable,
        universe_expr=universe_expr,
        weighted=weighted,
        value_pct=value,
        numerator_unweighted=len(num_rows),
        denominator_unweighted=len(denom_rows),
        denominator_weighted=denom_w,
        weight_var=weight_var if weighted else None,
    )


def correct_prevalence(
    df: pd.DataFrame, variable: str, *, analytical_universe: str | None = None
) -> PrevalenceResult:
    """The registry-correct prevalence: true universe + mandatory weighting.

    `analytical_universe` overrides the registry's *question* universe when the claim
    targets a narrower analytical denominator (e.g. insulin use among diagnosed
    diabetics is DIBEV_A == 1, not the prediabetes-inclusive question universe).
    """
    var = registry.get(variable)
    universe = analytical_universe if analytical_universe is not None else var.universe_expr
    return compute_prevalence(
        df,
        variable,
        universe_expr=universe,
        affirmative_codes=var.affirmative_codes,
        valid_codes=var.valid_codes,
        weighted=True,
        weight_var=var.weight,
    )


def fetch_microdata(dest_dir: str | Path = DATA_DIR) -> Path:
    """Download + unzip the NHIS 2023 Sample Adult public-use CSV (idempotent)."""
    import urllib.request

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    csv_path = dest_dir / "adult23.csv"
    if csv_path.exists():
        return csv_path
    zip_path = dest_dir / "adult23csv.zip"
    if not zip_path.exists():
        urllib.request.urlretrieve(NHIS_2023_ADULT_CSV_ZIP, zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
    if not csv_path.exists():
        raise RuntimeError(f"expected {csv_path} after unzip; archive layout changed")
    return csv_path
