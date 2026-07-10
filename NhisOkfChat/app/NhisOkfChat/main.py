"""AgentCore runtime entrypoint (thin shim).

This does NOT implement an agent. It configures the runtime and re-exports the single
reviewed agent from the vendored `nhis_okf` package. `build_runtime.py` vendors
`src/nhis_okf/` -> `./nhis_okf/` and the verified `.okf/` -> `./nhis_okf/okf_bundle/` at
package time (gitignored build artifacts; `src/nhis_okf` + `.okf/` stay the source of truth).

Before importing the agent it sets:
  * NHIS_RUNTIME_TOOLS=retrieval  -> only the verified-bundle retrieval tool is registered
    (pandas/analysis stay out of the CodeZip), and
  * NHIS_OKF_DIR -> the vendored `.okf/` bundle shipped beside the code.
`setdefault` lets a deploy-time env override win.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("NHIS_RUNTIME_TOOLS", "retrieval")
os.environ.setdefault(
    "NHIS_OKF_DIR", str(Path(__file__).resolve().parent / "nhis_okf" / "okf_bundle")
)

from nhis_okf.agentcore_app import app  # noqa: E402  (env must be set before import)

__all__ = ["app"]

if __name__ == "__main__":
    app.run()
