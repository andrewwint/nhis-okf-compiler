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
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_budgets as budgets,
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
        **kw,
    ) -> None:
        super().__init__(scope, cid, **kw)

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
            environment={"AGENT_RUNTIME_ARN": runtime_arn},
        )
        fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock-agentcore:InvokeAgentRuntime"],
                resources=[runtime_arn, runtime_arn + "/*"],
            )
        )
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

NhisOkfChatStack(
    app,
    "NhisOkfChat",
    runtime_arn=runtime_arn,
    alert_email=alert_email,
    budget_usd=budget_usd,
)
app.synth()
