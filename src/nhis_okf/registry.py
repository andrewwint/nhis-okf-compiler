"""Ground-truth domain knowledge for the NHIS 2023 diabetes slice.

This module is the **data-science skill's knowledge**, encoded as data: for each
variable, what it means, its valid response codes, its survey **universe** (the
skip-pattern that decides who was even asked), and the fact that NHIS estimates are
**weighted**. The verifier consults this registry as an *independent* source of truth
— it does NOT trust the method a concept claims to have used. That independence is what
lets verification catch a concept whose documented method is wrong.

Universe facts below were confirmed empirically against the 2023 Sample Adult
public-use file (adult23.csv), cross-checking who actually has a non-missing answer,
not assumed from the variable name. See `docs/PRODUCT.md` for why the universe matters.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# The mandatory final annual weight for the NHIS Sample Adult file. Unweighted counts
# are simply wrong for population estimates; this is not optional.
SAMPLE_ADULT_WEIGHT = "WTFA_A"

# Complex-survey design variables (Taylor-series linearization for standard errors).
# The lean slice reports weighted point estimates; design-based variance is a
# documented upgrade path (see SKILL.md), so these are recorded but not yet required.
DESIGN_STRATUM = "PSTRAT"
DESIGN_PSU = "PPSU"

# NHIS reserves these numeric codes for non-substantive answers across most items.
# 7 = Refused, 8 = Not Ascertained, 9 = Don't Know. They are never valid analysis values.
#
# REFERENCE ONLY — this constant is NOT applied automatically. Exclusion is enforced
# explicitly per variable via each Variable.valid_codes tuple, because the substantive
# range differs by item (e.g. continuous DIBAGETC_A reserves 96-99, not 7/8/9). When you
# add a variable, set valid_codes deliberately; do not rely on this list as a filter.
NONSUBSTANTIVE_CODES = (7, 8, 9, 77, 88, 99, 97, 98)


@dataclass(frozen=True)
class Variable:
    """Ground truth for one NHIS variable in the diabetes slice."""

    name: str
    label: str
    # The survey universe: the boolean condition (over the dataframe) for who was asked.
    # `None` means "asked of all Sample Adults" (no skip-pattern gate).
    universe_expr: str | None
    # Human-readable statement of that universe, for the OKF concept prose + audit.
    universe_text: str
    # Substantive response codes that count as valid for analysis.
    valid_codes: tuple[int, ...] = ()
    # Codes meaning "yes" when the variable is a yes/no item (for prevalence).
    affirmative_codes: tuple[int, ...] = ()
    weight: str = SAMPLE_ADULT_WEIGHT
    notes: str = ""
    related: tuple[str, ...] = field(default_factory=tuple)


# --- The diabetes slice -----------------------------------------------------------

REGISTRY: dict[str, Variable] = {
    "DIBEV_A": Variable(
        name="DIBEV_A",
        label="Ever told you had diabetes",
        universe_expr=None,  # asked of all sample adults
        universe_text="All sample adults.",
        valid_codes=(1, 2),
        affirmative_codes=(1,),
        notes=(
            "'Diagnosed diabetes' = DIBEV_A == 1, per CDC's published methodology. "
            "Borderline/prediabetes is a separate item (PREDIB_A). Note: no "
            "programmatic GESDIB_A (gestational) filter is applied — CDC does not "
            "exclude gestational-only cases from DIBEV_A == 1, and adding such a "
            "filter would shift the estimate ~0.9pp."
        ),
        related=("DIBINS_A", "DIBPILL_A", "DIBAGETC_A", "PREDIB_A"),
    ),
    "DIBINS_A": Variable(
        name="DIBINS_A",
        label="Currently takes insulin",
        # Empirically confirmed: answered by adults ever told they had diabetes OR
        # told they had prediabetes. NOT the whole sample. The *analytical* universe
        # for "insulin use among people with diagnosed diabetes" is the narrower
        # DIBEV_A == 1 (see analytical_universe below).
        universe_expr="(DIBEV_A == 1) | (PREDIB_A == 1)",
        universe_text=(
            "Adults ever told they had diabetes (DIBEV_A == 1) or prediabetes "
            "(PREDIB_A == 1). The clinically meaningful 'among diagnosed diabetics' "
            "denominator is the narrower DIBEV_A == 1."
        ),
        valid_codes=(1, 2),
        affirmative_codes=(1,),
        notes=(
            "Two traps: (1) computing over the whole sample inflates nothing but "
            "deflates the rate massively because most adults were never asked; "
            "(2) using the full *question* universe (incl. prediabetics) understates "
            "insulin use among actual diabetics. Both are wrong for the headline claim."
        ),
        related=("DIBEV_A", "DIBPILL_A"),
    ),
    "DIBPILL_A": Variable(
        name="DIBPILL_A",
        label="Currently takes diabetic pills",
        universe_expr="(DIBEV_A == 1) | (PREDIB_A == 1)",
        universe_text=(
            "Adults ever told they had diabetes (DIBEV_A == 1) or prediabetes "
            "(PREDIB_A == 1)."
        ),
        valid_codes=(1, 2),
        affirmative_codes=(1,),
        related=("DIBEV_A", "DIBINS_A"),
    ),
    "DIBAGETC_A": Variable(
        name="DIBAGETC_A",
        label="Age first told had diabetes (top-coded)",
        universe_expr="DIBEV_A == 1",
        universe_text="Adults ever told they had diabetes (DIBEV_A == 1).",
        # Continuous age; substantive values are < 96. 96/97/98/99 are reserved.
        valid_codes=tuple(range(0, 96)),
        notes="Top-coded at 85. Values >= 96 are non-substantive and must be dropped.",
        related=("DIBEV_A",),
    ),
    "PREDIB_A": Variable(
        name="PREDIB_A",
        label="Ever told you had prediabetes",
        universe_expr=None,
        universe_text="All sample adults.",
        valid_codes=(1, 2),
        affirmative_codes=(1,),
        related=("DIBEV_A",),
    ),
}


def get(name: str) -> Variable:
    if name not in REGISTRY:
        raise KeyError(
            f"{name!r} is not in the registry. Known variables: {sorted(REGISTRY)}"
        )
    return REGISTRY[name]


# The *analytical* universe for the headline insulin claim. Distinct from the question
# universe in the registry: the claim is about people with diagnosed diabetes, so the
# denominator is DIBEV_A == 1 — not the whole sample, and not the prediabetes-inclusive
# question universe. The verifier uses this when checking the canonical claim.
ANALYTICAL_UNIVERSES: dict[str, str] = {
    "DIBINS_A__among_diagnosed": "DIBEV_A == 1",
    "DIBPILL_A__among_diagnosed": "DIBEV_A == 1",
}
