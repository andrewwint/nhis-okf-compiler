"""Runtime configuration for the chat agent (model + region selection).

Local testing uses the Anthropic API (ANTHROPIC_API_KEY). The deploy target is Strands on
Bedrock AgentCore, which uses AWS credentials and a Bedrock model id. Both are overridable
by environment variables so nothing is hard-pinned.
"""

from __future__ import annotations

import os
from pathlib import Path

# Repo root: src/nhis_okf/config.py -> parents[2].
_REPO_ROOT = Path(__file__).resolve().parents[2]


def okf_dir() -> Path:
    """The verified OKF bundle directory.

    Defaults to the repo-relative `.okf/`; override with `NHIS_OKF_DIR` so a packaged
    runtime (the AgentCore CodeZip) can point retrieval at its bundled copy. Repo-relative
    default keeps local runs and tests unchanged.
    """
    override = os.environ.get("NHIS_OKF_DIR")
    return Path(override) if override else _REPO_ROOT / ".okf"


def aws_region() -> str:
    return os.environ.get("BEDROCK_REGION") or os.environ.get("AWS_REGION") or "us-east-1"


def anthropic_model_id() -> str:
    """Model id for the Anthropic API path (local testing)."""
    return os.environ.get("NHIS_ANTHROPIC_MODEL", "claude-sonnet-4-6")


def bedrock_model_id() -> str:
    """Model id for the Bedrock path (AgentCore deploy).

    Confirm the exact Bedrock model id available in your account/region before deploy;
    override with NHIS_BEDROCK_MODEL. Default is a recent Claude Sonnet inference profile.
    """
    return os.environ.get("NHIS_BEDROCK_MODEL", "us.anthropic.claude-sonnet-4-6")


def has_anthropic_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))
