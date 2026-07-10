# Project Context

## Purpose
`nhis-okf-compiler` compiles a messy, high-stakes public-health dataset (CDC NHIS) into a
*verified* Open Knowledge Format (OKF) bundle, with RAG-grounded search/chat over it. It
is both a Baton dogfood and a real tool.

The point is not the chatbot. The point is that verification is **execution-grounded**:
it runs the documented analysis against the real microdata with proper survey weights and
catches a statistic that is *structurally valid but statistically wrong* — a number whose
markdown is clean and whose links resolve, but which is wrong when actually computed. A
passive RAG ships that confidently; this catches it and quarantines it.

## Positioning
A demonstration of **composition**: Baton owns process (the gated loop, execution-grounded
verification, the audit trail) and stays domain-agnostic; a project-local **data-science
skill** owns the statistics (survey weighting, skip-pattern/universe logic, correctness).
Specific-first: one repo, one topic (diabetes), one survey year (NHIS 2023). Generalize to
other topics/years/datasets only when reuse earns it.

## Tech Stack
- Python 3.11; pandas / numpy for analysis; scikit-learn (TF-IDF) for local retrieval
- PyYAML for concept files and OKF frontmatter
- pytest for the test suite
- Chat: **Strands Agents** (grounded-answering agent with an OKF-retrieval tool), Anthropic
  API for local testing, **Amazon Bedrock** at deploy; **Bedrock AgentCore**
  (`BedrockAgentCoreApp`) as the runtime. Extractive answering works with no key/deps.

### Architecture principle: OKF is the substrate; vector search is a derived index
OKF (the verified markdown+YAML bundle) is the canonical knowledge. Any retrieval — TF-IDF
now, embeddings or a Bedrock Knowledge Base later — is an index **built from the verified
bundle**, never baked into the format. The invariant that matters is `index ⊆ verified OKF`:
only verified concepts are ever indexed, so a quarantined figure cannot be retrieved. The
chat agent's only data tool reads that same verified bundle.

## Project Conventions

### Code Style
- Plain, honest, ASCII-by-default. No reassuring filler.
- The registry is the independent source of statistical truth; verification never trusts a
  concept's own claimed method.

### Architecture Patterns
- `registry.py` — ground-truth domain knowledge (universe, valid codes, weights).
- `analysis.py` — one explicit prevalence engine that can express correct *and* flawed methods.
- `concepts/*.yaml` — documented claims (input); `verify.py` checks them by executing.
- `compiler.py` — emits only verified concepts to `.okf/variables/`; quarantines failures to `.okf/log.md`.
- `retrieval.py` / `chat.py` — local RAG over the verified bundle; the quarantined number is unreachable.

### Testing Strategy
- Tests run against the real microdata fixture (skip if absent).
- The load-bearing test asserts a concept passes lint **and** fails execution — the thesis.
- Validate OpenSpec changes with `openspec validate <change-id> --strict` (when the CLI is available).

### Git Workflow
- Branch before non-trivial work; the developer stays the credited author.
- Microdata and the venv are git-ignored; publish actions require approval.

## Important Constraints
- **Safety scope (non-negotiable):** public, de-identified, aggregate survey data only —
  not medical advice, no individual-level inference. Every figure carries its
  survey-weighted basis and source.
- **Verification must EXECUTE, not lint.** Survey weights are mandatory.
- Local-first; no live secrets in committed files.

## External Dependencies
- CDC NHIS 2023 Sample Adult public-use file (`adult23.csv`), fetched via `nhis fetch`.
- Optional `ANTHROPIC_API_KEY` for generative answering.
