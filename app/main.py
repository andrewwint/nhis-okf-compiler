"""AgentCore CLI runtime entrypoint (thin shim).

This is the packaged runtime's entrypoint. It does NOT implement an agent — it configures
the runtime mode and re-exports the single reviewed agent app from `nhis_okf.agentcore_app`.

Before importing the agent it:
  * sets `NHIS_RUNTIME_TOOLS=retrieval` so only the verified-bundle retrieval tool is
    registered (pandas/analysis stay out of the CodeZip), and
  * points `NHIS_OKF_DIR` at the `.okf/` bundle shipped alongside the source in the CodeZip.

`setdefault` is used so a deploy-time env override wins; locally these defaults make the
runtime pandas-free and self-contained.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("NHIS_RUNTIME_TOOLS", "retrieval")

# The CodeZip preserves the repo tree (codeLocation is the repo root, see agentcore.json):
# this file is at <root>/deploy/agentcore/app/main.py, so parents[3] is the CodeZip root,
# with `src/nhis_okf/` and `.okf/` beside it.
_ROOT = Path(__file__).resolve().parents[3]

# The agent source ships as `src/nhis_okf/` (not pip-installed — that would pull pandas).
# Put `src/` on the path so `import nhis_okf` resolves however the runtime sets sys.path.
_SRC = _ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Point retrieval at the bundled `.okf/` shipped in the CodeZip.
os.environ.setdefault("NHIS_OKF_DIR", str(_ROOT / ".okf"))

from nhis_okf.agentcore_app import app  # noqa: E402  (env must be set before import)

__all__ = ["app"]

if __name__ == "__main__":
    app.run()
