import pytest

from nhis_okf import analysis, concepts as concepts_mod
from nhis_okf.cli import SLICE_COLUMNS


@pytest.fixture(scope="session")
def df():
    try:
        return analysis.load_microdata(columns=SLICE_COLUMNS)
    except FileNotFoundError:
        pytest.skip("NHIS microdata not present; run `nhis fetch` to enable data tests")


@pytest.fixture(scope="session")
def concepts():
    return concepts_mod.load_all()
