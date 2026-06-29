"""Public chat endpoint: one Lambda behind a Function URL serves the chat page (GET) and
answers questions (POST) by invoking the Bedrock AgentCore runtime.

No user auth (deliberate, for a demo). Spend is bounded by: this input cap, the agent's
output token cap, Lambda reserved concurrency, and an AWS budget alarm. The Lambda holds the
only IAM permission to invoke the runtime; the browser never gets AWS credentials. Serving
the page from the same origin means there is no API URL to inject — the page POSTs to itself.

Note: the InvokeAgentRuntime response shape is confirmed on first deploy (it cannot be
unit-tested without the live runtime); the parsing below is defensive.
"""

import json
import os
from pathlib import Path

import boto3

RUNTIME_ARN = os.environ["AGENT_RUNTIME_ARN"]
MAX_QUESTION_CHARS = 600  # mirrors the agent-side cap
HERE = Path(__file__).parent

_client = boto3.client("bedrock-agentcore")


def _resp(code, content_type, body, cors=False):
    headers = {"content-type": content_type}
    if cors:
        headers["access-control-allow-origin"] = "*"
        headers["access-control-allow-methods"] = "POST, OPTIONS"
        headers["access-control-allow-headers"] = "content-type"
    return {"statusCode": code, "headers": headers, "body": body}


def _json(code, obj):
    return _resp(code, "application/json", json.dumps(obj), cors=True)


def _file(name, content_type):
    try:
        return _resp(200, content_type, (HERE / name).read_text())
    except FileNotFoundError:
        return _resp(404, "text/plain", "not found")


def handler(event, _context):
    http = event.get("requestContext", {}).get("http", {}) or {}
    method = http.get("method", "GET")
    path = event.get("rawPath", "/")

    if method == "OPTIONS":
        return _json(200, {})
    if method == "GET":
        if path in ("/", "/index.html"):
            return _file("index.html", "text/html")
        if path == "/app.js":
            return _file("app.js", "text/javascript")
        return _resp(404, "text/plain", "not found")

    # POST -> answer
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _json(400, {"error": "invalid JSON body"})
    question = (body.get("question") or "").strip()
    if not question:
        return _json(400, {"error": "no question provided"})
    if len(question) > MAX_QUESTION_CHARS:
        return _json(400, {"error": f"question too long (limit {MAX_QUESTION_CHARS} chars)"})

    resp = _client.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        payload=json.dumps({"question": question}).encode("utf-8"),
    )
    raw = resp.get("response")
    text = raw.read().decode("utf-8") if hasattr(raw, "read") else (raw or "")
    try:
        return _json(200, json.loads(text) if text else {"answer": ""})
    except json.JSONDecodeError:
        return _json(200, {"answer": text})
