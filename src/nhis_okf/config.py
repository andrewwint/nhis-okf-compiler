"""Runtime configuration for the chat agent (model + region selection).

Local testing uses the Anthropic API (ANTHROPIC_API_KEY). The deploy target is Strands on
Bedrock AgentCore, which uses AWS credentials and a Bedrock model id. Both are overridable
by environment variables so nothing is hard-pinned.
"""

from __future__ import annotations

import os


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
