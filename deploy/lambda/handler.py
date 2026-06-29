"""Public chat endpoint: one Lambda behind a Function URL serves the chat page (GET) and
answers questions (POST) by invoking the Bedrock AgentCore runtime.

No user login, but a public LLM endpoint needs abuse controls, so a POST must clear, in order:
  1. input length cap (rejected before any cost),
  2. Cloudflare Turnstile (CAPTCHA) verified server-side — a bot POSTing directly is rejected,
  3. a per-IP daily cap and a global daily cap in DynamoDB (atomic counters with TTL).
Then the agent (output token-capped) answers. Reserved concurrency + an AWS budget alarm sit
underneath. The browser never gets AWS credentials; only this Lambda can invoke the runtime.

If TURNSTILE_SECRET / RATE_TABLE are unset (local/dev), those checks are skipped.

Note: the InvokeAgentRuntime response shape is confirmed on first deploy (it cannot be
unit-tested without the live runtime); the parsing below is defensive.
"""

import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

import boto3

RUNTIME_ARN = os.environ["AGENT_RUNTIME_ARN"]
TURNSTILE_SECRET = os.environ.get("TURNSTILE_SECRET", "")
TURNSTILE_SITE_KEY = os.environ.get("TURNSTILE_SITE_KEY", "")
RATE_TABLE = os.environ.get("RATE_TABLE", "")
PER_IP_DAILY_LIMIT = int(os.environ.get("PER_IP_DAILY_LIMIT", "10"))
GLOBAL_DAILY_LIMIT = int(os.environ.get("GLOBAL_DAILY_LIMIT", "200"))
MAX_QUESTION_CHARS = 600
HERE = Path(__file__).parent

_agent = boto3.client("bedrock-agentcore")
_ddb = boto3.client("dynamodb") if RATE_TABLE else None


def _resp(code, content_type, body, cors=False):
    headers = {"content-type": content_type}
    if cors:
        headers.update({
            "access-control-allow-origin": "*",
            "access-control-allow-methods": "POST, OPTIONS",
            "access-control-allow-headers": "content-type",
        })
    return {"statusCode": code, "headers": headers, "body": body}


def _json(code, obj):
    return _resp(code, "application/json", json.dumps(obj), cors=True)


def _file(name, content_type, inject_site_key=False):
    try:
        text = (HERE / name).read_text()
    except FileNotFoundError:
        return _resp(404, "text/plain", "not found")
    if inject_site_key:
        text = text.replace("__TURNSTILE_SITE_KEY__", TURNSTILE_SITE_KEY)
    return _resp(200, content_type, text)


def _verify_turnstile(token: str, ip: str) -> bool:
    """Server-side CAPTCHA check. Skipped (returns True) when no secret is configured."""
    if not TURNSTILE_SECRET:
        return True
    data = urllib.parse.urlencode(
        {"secret": TURNSTILE_SECRET, "response": token or "", "remoteip": ip or ""}
    ).encode()
    req = urllib.request.Request(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify", data=data
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return bool(json.loads(r.read().decode()).get("success", False))
    except Exception:
        return False  # fail closed: if we can't verify, reject


def _under_cap(key: str, limit: int) -> bool:
    """Atomically increment a daily counter (TTL ~2 days) and report whether it's within limit."""
    if not _ddb:
        return True
    ttl = int(time.time()) + 2 * 86400
    resp = _ddb.update_item(
        TableName=RATE_TABLE,
        Key={"pk": {"S": key}},
        UpdateExpression="ADD #c :one SET #t = :ttl",
        ExpressionAttributeNames={"#c": "count", "#t": "ttl"},
        ExpressionAttributeValues={":one": {"N": "1"}, ":ttl": {"N": str(ttl)}},
        ReturnValues="UPDATED_NEW",
    )
    return int(resp["Attributes"]["count"]["N"]) <= limit


def _rate_ok(client_ip: str) -> tuple[bool, str]:
    day = time.strftime("%Y-%m-%d", time.gmtime())
    if not _under_cap(f"ip#{client_ip}#{day}", PER_IP_DAILY_LIMIT):
        return False, f"per-IP daily limit ({PER_IP_DAILY_LIMIT}) reached — try again tomorrow"
    if not _under_cap(f"global#{day}", GLOBAL_DAILY_LIMIT):
        return False, "the demo's daily query limit was reached — try again tomorrow"
    return True, ""


def handler(event, _context):
    http = event.get("requestContext", {}).get("http", {}) or {}
    method = http.get("method", "GET")
    path = event.get("rawPath", "/")
    client_ip = http.get("sourceIp", "")

    if method == "OPTIONS":
        return _json(200, {})
    if method == "GET":
        if path in ("/", "/index.html"):
            return _file("index.html", "text/html", inject_site_key=True)
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
    if not _verify_turnstile(body.get("turnstile_token", ""), client_ip):
        return _json(403, {"error": "human verification failed — please retry the checkbox"})
    ok, why = _rate_ok(client_ip)
    if not ok:
        return _json(429, {"error": why})

    resp = _agent.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        payload=json.dumps({"question": question}).encode("utf-8"),
    )
    raw = resp.get("response")
    text = raw.read().decode("utf-8") if hasattr(raw, "read") else (raw or "")
    try:
        return _json(200, json.loads(text) if text else {"answer": ""})
    except json.JSONDecodeError:
        return _json(200, {"answer": text})
