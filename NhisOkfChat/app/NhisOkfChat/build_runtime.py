"""Assemble the self-contained CodeZip runtime (build artifact — run before `agentcore package`).

The AgentCore CodeZip zips this dir (`app/NhisOkfChat/`). `nhis_okf` isn't on PyPI, so it
can't be a pip dependency at AWS runtime — it must ride inside the zip. This copies the
single source of truth into gitignored artifacts here:

  <repo>/src/nhis_okf/  ->  ./nhis_okf/
  <repo>/.okf/          ->  ./nhis_okf/okf_bundle/

Idempotent. `src/nhis_okf/` + `.okf/` remain canonical; `./nhis_okf/` is disposable.
"""

from __future__ import annotations

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]  # NhisOkfChat/app/NhisOkfChat -> NhisOkfChat/app -> NhisOkfChat -> repo
SRC = REPO_ROOT / "src" / "nhis_okf"
OKF = REPO_ROOT / ".okf"

VENDOR = HERE / "nhis_okf"
BUNDLE = VENDOR / "okf_bundle"


def _copy_tree(src: Path, dst: Path) -> int:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return sum(1 for _ in dst.rglob("*") if _.is_file())


def main() -> None:
    if not SRC.is_dir():
        raise SystemExit(f"source package not found: {SRC}")
    if not OKF.is_dir():
        raise SystemExit(f"verified bundle not found: {OKF} (run `nhis compile` first)")
    n_code = _copy_tree(SRC, VENDOR)
    n_bundle = _copy_tree(OKF, BUNDLE)
    print(f"vendored nhis_okf: {n_code} files -> {VENDOR}")
    print(f"vendored bundle:   {n_bundle} files -> {BUNDLE}")


if __name__ == "__main__":
    main()
