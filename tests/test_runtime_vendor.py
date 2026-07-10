"""The CodeZip payload is *vendored* from the single source of truth, faithfully.

`app/build_runtime.py` copies `src/nhis_okf/` -> `app/nhis_okf/` and `.okf/` ->
`app/nhis_okf/okf_bundle/` so the codeLocation is self-contained (nhis_okf is not on PyPI).
`app/nhis_okf/` is a gitignored build artifact, so we run the build here and assert the copy
is byte-identical — the build step is the only producer, and it must never drift.
"""

import filecmp
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PKG = REPO_ROOT / "src" / "nhis_okf"
SRC_BUNDLE = REPO_ROOT / ".okf"
DEST_PKG = REPO_ROOT / "app" / "nhis_okf"
DEST_BUNDLE = DEST_PKG / "okf_bundle"


def _assert_identical(left: Path, right: Path, *, ignore=()) -> None:
    """Recursively assert two trees are byte-identical (ignoring named entries)."""
    cmp = filecmp.dircmp(left, right, ignore=list(ignore))
    assert not cmp.left_only, f"only in {left}: {cmp.left_only}"
    assert not cmp.right_only, f"only in {right}: {cmp.right_only}"
    assert not cmp.diff_files, f"differing files under {left}: {cmp.diff_files}"
    for sub in cmp.common_dirs:
        _assert_identical(left / sub, right / sub, ignore=ignore)


def test_build_runtime_vendors_faithfully():
    res = subprocess.run(
        [sys.executable, str(REPO_ROOT / "app" / "build_runtime.py")],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr

    # Vendored package == src/nhis_okf (the build strips caches and the nested okf_bundle).
    _assert_identical(SRC_PKG, DEST_PKG, ignore=("__pycache__", "okf_bundle"))
    # Vendored bundle == the verified .okf, byte-for-byte.
    _assert_identical(SRC_BUNDLE, DEST_BUNDLE, ignore=("__pycache__",))
