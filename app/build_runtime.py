#!/usr/bin/env python3
"""Assemble the self-contained AgentCore CodeZip payload under `app/`.

The CodeZip must be self-contained: AgentCore installs `app/requirements.txt` (third-party
only) at runtime and puts `app/` on `sys.path`, but it cannot reach the repo-root
`src/nhis_okf/` or `.okf/`. `nhis_okf` is not on PyPI, so it must be *vendored* into the
codeLocation. This script is the single producer of those build artifacts (gitignored, never
committed — `src/nhis_okf/` and `.okf/` stay the one source of truth):

  * `src/nhis_okf/`  -> `app/nhis_okf/`            (an importable package beside main.py)
  * `.okf/`          -> `app/nhis_okf/okf_bundle/`  (the verified bundle, found by
                                                     `config._shipped_bundle_dir()`)

Idempotent. Run before `agentcore package`:

    python app/build_runtime.py
    agentcore package
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
SRC_PKG = REPO_ROOT / "src" / "nhis_okf"
SRC_BUNDLE = REPO_ROOT / ".okf"
DEST_PKG = APP_DIR / "nhis_okf"
DEST_BUNDLE = DEST_PKG / "okf_bundle"

_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "okf_bundle")


def main() -> int:
    if not SRC_PKG.is_dir():
        print(f"error: source package not found at {SRC_PKG}", file=sys.stderr)
        return 1
    if not SRC_BUNDLE.is_dir():
        print(f"error: verified bundle not found at {SRC_BUNDLE}", file=sys.stderr)
        return 1

    if DEST_PKG.exists():
        shutil.rmtree(DEST_PKG)
    shutil.copytree(SRC_PKG, DEST_PKG, ignore=_IGNORE)
    shutil.copytree(SRC_BUNDLE, DEST_BUNDLE)

    n_py = sum(1 for _ in DEST_PKG.rglob("*.py"))
    n_bundle = sum(1 for _ in DEST_BUNDLE.rglob("*") if _.is_file())
    print(f"vendored nhis_okf: {n_py} modules -> {DEST_PKG}")
    print(f"vendored bundle:   {n_bundle} files -> {DEST_BUNDLE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
