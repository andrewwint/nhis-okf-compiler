"""CDK app for the public NHIS-OKF chat endpoint.

One Lambda behind a Function URL (no auth) serves the chat page and answers by invoking the
Bedrock AgentCore runtime. Spend controls: Lambda reserved concurrency + the agent's token
cap + an AWS monthly budget alarm. No S3/CloudFront — the Lambda serves the page from the
same origin.

Context parameters (pass with -c, or edit cdk.json):
  runtimeArn   the Bedrock AgentCore runtime ARN (from `agentcore launch`)
  alertEmail   email for the budget alarm
  budgetUsd    monthly budget threshold (default 20)

`cdk synth` runs fully locally and creates no AWS resources.
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    RemovalPolicy,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_budgets as budgets,
    aws_dynamodb as dynamodb,
)
from constructs import Construct


class NhisOkfChatStack(Stack):
    def __init__(
        self,
        scope: Construct,
        cid: str,
        *,
        runtime_arn: str,
        alert_email: str,
        budget_usd: float,
        turnstile_secret: str,
        turnstile_site_key: str,
        per_ip_limit: int,
        global_limit: int,
        **kw,
    ) -> None:
        super().__init__(scope, cid, **kw)

        # Daily rate-limit counters (per-IP + global), auto-expiring via TTL.
        rate_table = dynamodb.Table(
            self,
            "RateLimit",
            partition_key=dynamodb.Attribute(
                name="pk", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.DESTROY,
        )

        fn = _lambda.Function(
            self,
            "ChatFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("../lambda"),
            timeout=Duration.seconds(60),
            memory_size=256,
            # No auth on the URL, so throttle a flood at the concurrency level.
            reserved_concurrent_executions=2,
            environment={
                "AGENT_RUNTIME_ARN": runtime_arn,
                "TURNSTILE_SECRET": turnstile_secret,
                "TURNSTILE_SITE_KEY": turnstile_site_key,
                "RATE_TABLE": rate_table.table_name,
                "PER_IP_DAILY_LIMIT": str(per_ip_limit),
                "GLOBAL_DAILY_LIMIT": str(global_limit),
            },
        )
        fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock-agentcore:InvokeAgentRuntime"],
                resources=[runtime_arn, runtime_arn + "/*"],
            )
        )
        rate_table.grant_read_write_data(fn)
        url = fn.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.NONE,
            cors=_lambda.FunctionUrlCorsOptions(
                allowed_origins=["*"], allowed_methods=[_lambda.HttpMethod.ALL]
            ),
        )

        budgets.CfnBudget(
            self,
            "MonthlyBudget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_type="COST",
                time_unit="MONTHLY",
                budget_limit=budgets.CfnBudget.SpendProperty(
                    amount=budget_usd, unit="USD"
                ),
            ),
            notifications_with_subscribers=[
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        notification_type="ACTUAL",
                        comparison_operator="GREATER_THAN",
                        threshold=threshold,
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="EMAIL", address=alert_email
                        )
                    ],
                )
                for threshold in (50, 80, 100)
            ],
        )

        CfnOutput(self, "ChatUrl", value=url.url, description="Public chat URL (no auth)")


app = cdk.App()
runtime_arn = (
    app.node.try_get_context("runtimeArn")
    or "arn:aws:bedrock-agentcore:us-east-1:000000000000:runtime/PLACEHOLDER"
)
alert_email = app.node.try_get_context("alertEmail") or "you@example.com"
budget_usd = float(app.node.try_get_context("budgetUsd") or 20)
turnstile_secret = app.node.try_get_context("turnstileSecret") or ""
turnstile_site_key = app.node.try_get_context("turnstileSiteKey") or ""
per_ip_limit = int(app.node.try_get_context("perIpLimit") or 10)
global_limit = int(app.node.try_get_context("globalLimit") or 200)

NhisOkfChatStack(
    app,
    "NhisOkfChat",
    runtime_arn=runtime_arn,
    alert_email=alert_email,
    budget_usd=budget_usd,
    turnstile_secret=turnstile_secret,
    turnstile_site_key=turnstile_site_key,
    per_ip_limit=per_ip_limit,
    global_limit=global_limit,
)
app.synth()
