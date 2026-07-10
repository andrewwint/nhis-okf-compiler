"""Local smoke test for the packaged retrieval-only runtime path (NO AWS).

`bedrock_agentcore` is a deploy-only dependency and is not installed locally, so the thin
`deploy/agentcore/app/main.py` (which imports `nhis_okf.agentcore_app`) cannot be imported
here. Instead we exercise the exact behaviors that entrypoint configures:

  * retrieval-only mode + NHIS_OKF_DIR set, the grounded extractive answer path returns the
    verified figure (a grounded query) and refuses an off-bundle query, and
  * that path stays pandas-free.

The live generative agent on Bedrock is confirmed only by the real deploy.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from nhis_okf import chat

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_retrieval_only_grounded_answer(monkeypatch):
    monkeypatch.setenv("NHIS_RUNTIME_TOOLS", "retrieval")
    monkeypatch.setenv("NHIS_OKF_DIR", str(REPO_ROOT / ".okf"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ans = chat.answer("insulin use among adults with diabetes", generative=False)
    assert ans.mode == "extractive"
    assert "31.96" in ans.text
    assert "not medical advice" in ans.text


def test_retrieval_only_refuses_off_bundle(monkeypatch):
    monkeypatch.setenv("NHIS_RUNTIME_TOOLS", "retrieval")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ans = chat.answer("prevalence of asthma among adults", generative=False)
    # Never fabricates and never surfaces the quarantined naive figure.
    assert "3.66" not in ans.text
    assert "asthma" not in ans.text.lower() or "No verified concept" in ans.text


def test_deploy_entrypoint_is_a_thin_reexport():
    """The runtime entrypoint re-exports the source agent app rather than reimplementing it.
    We can't import it locally (bedrock_agentcore is deploy-only), so assert structurally:
    it imports the app from nhis_okf.agentcore_app and defines no agent of its own."""
    main = (REPO_ROOT / "deploy" / "agentcore" / "app" / "main.py").read_text()
    assert "from nhis_okf.agentcore_app import app" in main
    assert 'setdefault("NHIS_RUNTIME_TOOLS", "retrieval")' in main
    assert "NHIS_OKF_DIR" in main
    assert "BedrockAgentCoreApp(" not in main  # no parallel agent construction


def test_full_retrieval_answer_path_is_pandas_free():
    """End-to-end retrieval-only answer in a fresh process must not load our pandas-bearing
    `analysis`/`compiler` modules (the runtime installs no pandas). See the note in
    tests/test_chat.py on why we assert on our modules, not `pandas` itself."""
    code = (
        "import os, sys\n"
        "os.environ['NHIS_RUNTIME_TOOLS'] = 'retrieval'\n"
        "os.environ.pop('ANTHROPIC_API_KEY', None)\n"
        "from nhis_okf import chat\n"
        "ans = chat.answer('insulin use among adults with diabetes', generative=False)\n"
        "assert '31.96' in ans.text, ans.text\n"
        "assert 'nhis_okf.analysis' not in sys.modules, 'analysis imported on answer path'\n"
        "assert 'nhis_okf.compiler' not in sys.modules, 'compiler imported on answer path'\n"
        "print('OK')\n"
    )
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == "OK"
