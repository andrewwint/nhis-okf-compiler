"""The verified-bundle location is overridable via NHIS_OKF_DIR so a packaged runtime can
read a bundled copy. Default (unset) is the repo-relative `.okf/` — unchanged behavior.

`config.okf_dir()` reads the env at call time; `compiler.OKF_DIR`/`VARIABLES_DIR` (which
retrieval consumes) bind it at import time — the runtime sets NHIS_OKF_DIR before importing
the agent, so this test drives the redirect in a fresh subprocess to mirror that.
"""

import shutil
import subprocess
import sys
from pathlib import Path

from nhis_okf import config

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_okf_dir_defaults_to_repo_relative(monkeypatch):
    monkeypatch.delenv("NHIS_OKF_DIR", raising=False)
    assert config.okf_dir() == REPO_ROOT / ".okf"


def test_okf_dir_honors_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("NHIS_OKF_DIR", str(tmp_path))
    assert config.okf_dir() == tmp_path


def test_okf_dir_falls_back_to_shipped_bundle(monkeypatch, tmp_path):
    """When the env is unset and the repo-relative `.okf/` is absent (the deployed CodeZip),
    resolve to the bundle shipped inside the installed package (staged into `okf_bundle/`)."""
    monkeypatch.delenv("NHIS_OKF_DIR", raising=False)
    # Simulate a package install with no repo-relative bundle beside it.
    monkeypatch.setattr(config, "_REPO_ROOT", tmp_path)
    assert not (tmp_path / ".okf").exists()
    assert config.okf_dir() == config._shipped_bundle_dir()


def test_override_redirects_retrieval(tmp_path):
    """With NHIS_OKF_DIR set before import, retrieval reads the bundle from that directory."""
    alt = tmp_path / "bundle"
    (alt / "variables").mkdir(parents=True)
    # Copy exactly one real verified concept into the alternate bundle.
    src = REPO_ROOT / ".okf" / "variables" / "DIBINS_A.md"
    shutil.copy(src, alt / "variables" / "DIBINS_A.md")

    code = (
        "from nhis_okf.retrieval import load_bundle, VARIABLES_DIR\n"
        "concepts = load_bundle()\n"
        "ids = sorted(c.id for c in concepts)\n"
        "print(str(VARIABLES_DIR))\n"
        "print(','.join(ids))\n"
    )
    import os
    env = {**os.environ, "NHIS_OKF_DIR": str(alt)}
    res = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env
    )
    assert res.returncode == 0, res.stderr
    out_lines = res.stdout.strip().splitlines()
    assert out_lines[0] == str(alt / "variables")
    assert out_lines[1] == "DIBINS_A"  # only the one concept in the alternate bundle
