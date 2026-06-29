# Sample queries — the deployed grounded agent

Real responses from the agent deployed on **Amazon Bedrock AgentCore** (`agentcore invoke`),
Claude Sonnet 4.5 over the verified OKF bundle. The agent answers **only** from verified
concepts: it cites the concept id, quotes the survey-weighted figure and its design-based
95% CI, refuses when the bundle has no answer, and never invents a number.

## 1. A verified figure

```
$ agentcore invoke '{"question": "what share of adults with diabetes take insulin?"}'
```
> Based on verified NHIS data, **31.96%** (95% CI: 30.08–33.84%) of U.S. adults with
> diagnosed diabetes currently take insulin **[DIBINS_A]**. Survey-weighted estimate, 2023.

## 2. Refusal — no concept in the bundle

```
$ agentcore invoke '{"question": "what is the prevalence of asthma among US adults?"}'
```
> I cannot answer this question from the verified NHIS bundle. The search did not return any
> verified concepts related to asthma prevalence among US adults.

## 3. Grounded — and honest about its boundary

```
$ agentcore invoke '{"question": "how does survey weighting change diabetes prevalence?"}'
```
> The survey-weighted prevalence of diagnosed diabetes among U.S. adults in 2023 is **9.8%**
> (95% CI 9.39–10.20) **[DIBEV_A]**, with a design effect (DEFF) of **1.41** … However, I
> cannot provide the specific difference between weighted and unweighted prevalence from the
> verified bundle, as those comparative figures are not returned by the search.

## Why this matters

Asked the same weighting question, a frontier chat model with no grounding confidently
produced an unweighted **11.2%** figure, race/age subgroup tables, and a fabricated claim
about this project's internals — none of it verified here. The grounded agent **refused to
state the unweighted number** — even though 11.2% is a real value we computed — purely because
it is not a verified concept in the bundle.

Grounding makes the agent *less* willing to guess than a strong ungrounded model. That is the
point: every figure it serves passed execution-grounded verification, and it would rather
refuse than fabricate.
