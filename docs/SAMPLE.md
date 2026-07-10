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

---

# Sample queries — `nhis analyze` (ad-hoc subpopulation lookups)

Beyond the pre-authored concepts, `nhis analyze` runs **ad-hoc survey-weighted lookups over
a subpopulation** you define. You filter across rows with an arbitrary universe expression
(the *means*); the command returns only a **weighted aggregate with its design-based 95%
CI** (the *output*). It never emits individual records — the aggregate-only safety scope,
enforced in code — and it is **grounded-or-refuse**: it answers only for a variable backed
by a verified concept in the compiled bundle.

```bash
nhis analyze --variable <VAR> --universe "<pandas expr>" --stat prevalence|mean|quantile [--q 0.5]
```

All figures below are real output against the CDC NHIS 2023 public-use file.

## Prevalence within a subpopulation

Insulin use **among adults with diagnosed diabetes** (`DIBEV_A == 1`):

```
$ nhis analyze --variable DIBINS_A --universe "DIBEV_A == 1" --stat prevalence
DIBINS_A prevalence: 31.96% (95% CI 30.08-33.84%; design-based SE 0.96; weighted by WTFA_A;
  universe: DIBEV_A == 1; n=3291 unweighted, denominator 25,248,324 weighted)
```

Hypertension-medication use **among adults told they have hypertension** (`HYPEV_A == 1`):

```
$ nhis analyze --variable HYPMED_A --universe "HYPEV_A == 1" --stat prevalence
HYPMED_A prevalence: 79.62% (95% CI 78.63-80.61%; design-based SE 0.50; weighted by WTFA_A;
  universe: HYPEV_A == 1; n=11083 unweighted, denominator 83,085,709 weighted)
```

### The universe changes the number

Widening the same insulin question to **diabetes _or_ prediabetes** roughly halves the
rate — prediabetics rarely use insulin. This is why the universe is stated with every
figure:

```
$ nhis analyze --variable DIBINS_A --universe "(DIBEV_A == 1) | (PREDIB_A == 1)" --stat prevalence
DIBINS_A prevalence: 16.75% (95% CI 15.66-17.84%; design-based SE 0.56; weighted by WTFA_A;
  universe: (DIBEV_A == 1) | (PREDIB_A == 1); n=6324 unweighted, denominator 49,736,586 weighted)
```

## Weighted mean and quantile (continuous variables)

Mean and median **age first told had diabetes** among diagnosed adults (non-substantive
codes 96–99 dropped, survey-weighted):

```
$ nhis analyze --variable DIBAGETC_A --universe "DIBEV_A == 1" --stat mean
DIBAGETC_A mean: 47.41 (95% CI 46.75-48.08; design-based SE 0.34; weighted by WTFA_A;
  universe: DIBEV_A == 1; n=3170 unweighted, denominator 24,498,399 weighted)

$ nhis analyze --variable DIBAGETC_A --universe "DIBEV_A == 1" --stat quantile --q 0.5
DIBAGETC_A quantile (q=0.5): 50.00 (95% CI 48.00-50.00; design-based SE 0.01; weighted by
  WTFA_A; universe: DIBEV_A == 1; n=3170 unweighted, denominator 24,498,399 weighted)
```

## Sex-stratified subpopulation

The same query surface stratifies by any loaded column with **no engine change** — here the
survey-weighted **mean weight** of U.S. adults by sex (`SEX_A`: 1 = male, 2 = female). Each
call returns an aggregate estimate and its design-based CI, never any individual rows:

```
$ nhis analyze --variable WEIGHTLBTC_A --universe "SEX_A == 1" --stat mean
WEIGHTLBTC_A mean: 195.00 (95% CI 194.20-195.81; design-based SE 0.41; weighted by WTFA_A;
  universe: SEX_A == 1; n=12438 unweighted, denominator 115,446,875 weighted)

$ nhis analyze --variable WEIGHTLBTC_A --universe "SEX_A == 2" --stat mean
WEIGHTLBTC_A mean: 162.68 (95% CI 161.90-163.47; design-based SE 0.40; weighted by WTFA_A;
  universe: SEX_A == 2; n=14599 unweighted, denominator 120,035,788 weighted)
```

## Refusals (grounded-or-refuse, and no fabricated numbers)

A variable with no verified concept is refused, and the message lists what is available:

```
$ nhis analyze --variable AGE_A --universe "DIBEV_A == 1" --stat mean
refused: 'AGE_A' is not backed by a verified concept in the compiled bundle. Run
  `nhis compile` first, or choose one of: DIBAGETC_A, DIBEV_A, DIBINS_A, DIBPILL_A,
  HYPEV_A, HYPMED_A, PREDIB_A.
```

An empty subpopulation refuses rather than reporting a confidently-wrong `0.0`:

```
$ nhis analyze --variable DIBAGETC_A --universe "DIBEV_A == 999" --stat mean
could not compute: empty subpopulation: universe 'DIBEV_A == 999' matches no substantive
  DIBAGETC_A rows — no weighted estimate is defined
```

Every estimate is weighted by `WTFA_A` with a design-based CI (Taylor linearization for
proportions/means; Woodruff for quantiles) using the `PSTRAT`/`PPSU` design variables.
