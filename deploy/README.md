# Deploy: public NHIS-OKF chat (Bedrock AgentCore + Lambda Function URL)

A demo deployment. **No user login**, but a public LLM endpoint is defended in depth:
Cloudflare Turnstile (CAPTCHA, verified server-side), a per-IP daily cap and a global daily
cap (DynamoDB), the agent's output token cap, the Lambda input cap, Lambda reserved
concurrency (2), and an AWS monthly budget alarm.

```
browser ──> Lambda Function URL (public, no auth)   serves the page (GET) + answers (POST)
                 │  bedrock-agentcore:InvokeAgentRuntime  (IAM; only the Lambda can call it)
                 ▼
            Bedrock AgentCore runtime  (Strands agent, src/nhis_okf/agentcore_app.py)
                 │  search_verified_okf -> the verified .okf bundle
                 ▼
            Bedrock claude-sonnet-4-6  (output capped at 600 tokens)
```

## Cost (us-east-1, rough)
- Idle ≈ $0 (everything is consumption-priced).
- ~$0.01–0.02 per question (Sonnet 4.6, capped). A **$20/mo** budget ≈ ~1,000–1,500 questions.
- **Residual risk (much reduced, not zero):** CAPTCHA stops casual bots and direct POSTs;
  the per-IP cap (10/day) limits any one client; the global cap (200/day) is the hard query
  ceiling; reserved concurrency throttles bursts; the budget *alarms* (it does not hard-stop
  Bedrock). A determined attacker rotating IPs is still bounded by the global cap + budget.
  Still: take the stack down (`cdk destroy`) when the demo is over rather than leaving it up.

## Prerequisites
- AWS creds (`AWS_PROFILE=AdministratorAccess-790768631355`), region `us-east-1`.
- Bedrock model access for `claude-sonnet-4-6` (confirmed enabled).
- `pip install bedrock-agentcore-starter-toolkit` (the `agentcore` CLI); Node ≥ 20 for `cdk`.
- **Cloudflare Turnstile** (free): create a widget at dash.cloudflare.com → Turnstile to get
  a **site key** (public) and **secret key**. Pass them to `cdk deploy` below. (If you skip
  this — omit the two `turnstile*` context values — the CAPTCHA check is disabled and only the
  rate caps + budget apply; fine for a brief supervised demo, not for leaving it up.)

## 1. Deploy the AgentCore runtime
From the repo root, with the `.okf/` bundle present (it is committed):
```bash
agentcore configure --entrypoint src/nhis_okf/agentcore_app.py \
  --requirements-file deploy/agentcore/requirements.txt
agentcore launch          # builds the container, pushes to ECR, creates the runtime
```
Note the **runtime ARN** it prints. (First-deploy checks: confirm the container can import
`nhis_okf` — `src/` on `PYTHONPATH` — and reach `.okf/`; confirm the `InvokeAgentRuntime`
response shape matches `deploy/lambda/handler.py`'s parsing.)

## 2. Deploy the public endpoint (CDK)
```bash
cd deploy/infra
pip install -r requirements.txt           # aws-cdk-lib (synth-only; the Lambda uses boto3)
cdk deploy \
  -c runtimeArn=<RUNTIME_ARN_FROM_STEP_1> \
  -c alertEmail=you@example.com \
  -c budgetUsd=20 \
  -c turnstileSiteKey=<CF_SITE_KEY> -c turnstileSecret=<CF_SECRET> \
  -c perIpLimit=10 -c globalLimit=200
```
The abuse controls are tunable: `perIpLimit` (default 10/IP/day), `globalLimit` (default
200/day). Omit the `turnstile*` values to disable the CAPTCHA (supervised-demo only).
`cdk synth` runs locally and creates nothing; `cdk deploy` provisions the Lambda + Function
URL + IAM + the budget. The stack output **ChatUrl** is your public chat page.

Confirm the **budget subscription email** (AWS sends a one-time confirmation).

## 3. Test
Open `ChatUrl` in a browser and ask: *"what share of adults with diabetes take insulin?"*
You should get the verified **31.96%** with its CI and the not-medical-advice framing; an
off-bundle question (e.g. asthma) should be refused.

## 4. Teardown (do this when the demo is done)
```bash
cd deploy/infra && cdk destroy
agentcore delete            # remove the runtime (and its ECR image)
```

## What is verified vs. confirmed-on-deploy
- **Verified locally:** the CDK stack synthesizes to a valid template with the intended
  guardrails (reserved concurrency 2, Function URL auth NONE, $20 budget); Lambda/handler
  Python is syntax-clean.
- **Confirmed on first deploy (cannot be unit-tested without the live runtime):** the
  AgentCore container packaging (import path + bundle access) and the exact
  `InvokeAgentRuntime` request/response shape. Iterate here on the first `agentcore launch`.
