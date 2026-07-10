"""AgentCore CLI runtime entrypoint (thin shim).

This is the packaged runtime's entrypoint. It does NOT implement an agent — it configures
the runtime mode and re-exports the single reviewed agent app from `nhis_okf.agentcore_app`.

`nhis_okf` is vendored beside this file into `app/nhis_okf/` by `app/build_runtime.py` (a
gitignored build artifact — `src/nhis_okf/` stays the source of truth), and AgentCore puts
the codeLocation on `sys.path`, so `import nhis_okf` resolves inside the CodeZip. Third-party
deps (strands, bedrock-agentcore, numpy, scikit-learn, PyYAML) install from
`app/requirements.txt` at runtime — no pandas.

Before importing the agent it:
  * sets `NHIS_RUNTIME_TOOLS=retrieval` so only the verified-bundle retrieval tool is
    registered (pandas/analysis stay out of the CodeZip), and
  * points `NHIS_OKF_DIR` at the vendored `.okf/` bundle shipped inside the package.

`setdefault` is used so a deploy-time env override wins.
"""

from __future__ import annotations

import os

os.environ.setdefault("NHIS_RUNTIME_TOOLS", "retrieval")

# Point retrieval at the bundle vendored inside the package. `config.okf_dir()` already falls
# back to this same location when the env is unset; setting it explicitly keeps the runtime's
# source of truth obvious.
from nhis_okf import config  # noqa: E402

os.environ.setdefault("NHIS_OKF_DIR", str(config._shipped_bundle_dir()))

from nhis_okf.agentcore_app import app  # noqa: E402  (env must be set before import)

__all__ = ["app"]

if __name__ == "__main__":
    app.run()
