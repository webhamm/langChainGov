# langChainGov

A personal learning sandbox for building LangChain applications against a local model and trying out guardrail techniques on them. The model is served by a local [LiteLLM](https://docs.litellm.ai/) proxy that fronts a local Llama; nothing here needs a cloud API key.

The plan lives in `specs/`: `mission.md` (why and what), `tech-stack.md` (how), `roadmap.md` (phases). Each phase has its own folder with requirements, a plan, and a validation checklist.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (it installs the pinned Python 3.12 for you)
- A LiteLLM proxy running locally, by default on `http://localhost:4000`, with an API key

## Setup

```sh
uv sync
cp .env.example .env   # then fill in LITELLM_API_KEY and LANGCHAINGOV_MODEL
```

Settings (environment variables or `.env`):

| Variable | Default | Meaning |
| --- | --- | --- |
| `LITELLM_API_KEY` | (required) | Key the LiteLLM proxy expects (`LITELLM_MASTER_KEY` is accepted too, so LiteLLM's own `.env` works) |
| `LANGCHAINGOV_MODEL` | (required) | Model name as LiteLLM exposes it |
| `LANGCHAINGOV_BASE_URL` | `http://localhost:4000/v1` | OpenAI-compatible endpoint |
| `LANGCHAINGOV_TEMPERATURE` | `0` | Sampling temperature |
| `LANGCHAINGOV_BLOCKLIST` | `blorptium,zanthar protocol` | Comma-separated words for the `keyword-blocklist` guard (fictional defaults) |
| `LANGCHAINGOV_PII_MODE` | `redact` | `redact` or `block`, for the `pii-regex` guard |
| `LANGCHAINGOV_TOPICS` | plant-care words | Comma-separated topic words for the `topic-allowlist` guard |
| `LANGCHAINGOV_JUDGE_MODEL` | (chat model) | Model for the `llm-judge` guard; empty reuses `LANGCHAINGOV_MODEL` |
| `LANGCHAINGOV_JUDGE_RUBRIC` | (built-in) | Path to a plain-text rubric file for the `llm-judge` guard |
| `LANGCHAINGOV_HOOKS_BLOCK_PHRASE` | `developer mode` | `lc-custom-hooks`: a prompt containing this phrase is blocked |
| `LANGCHAINGOV_HOOKS_REWRITE_FROM` / `_TO` | `blorptium` / `[a mineral]` | `lc-custom-hooks`: word rewritten in the reply |
| `LANGCHAINGOV_GR_PII_ENTITIES` | structured identifiers | `gr-pii`: Presidio entity types to detect; add `PERSON,LOCATION` etc. to opt into NER-based ones |
| `LANGCHAINGOV_GR_TOXIC_THRESHOLD` | `0.5` | `gr-toxic`: block when any toxicity label scores at or above this |
| `LANGCHAINGOV_GR_TOPIC_THRESHOLD` | `0.5` | `gr-topic`: the top topic must be valid and score at least this |
| `LANGCHAINGOV_GR_VALID_TOPICS` / `_INVALID_TOPICS` | plant-care / finance, taxes, ... | `gr-topic`: candidate labels for the zero-shot classifier |

## Commands

```sh
uv run langchaingov models                      # what the proxy exposes; pick one for LANGCHAINGOV_MODEL
uv run langchaingov chat "Say hello in five words"
uv run langchaingov chat --system "You are terse." --model other-model --json "hi"
uv run langchaingov version
```

### Guardrails

```sh
uv run langchaingov guard list
uv run langchaingov guard run --guard keyword-blocklist "Tell me about blorptium"
uv run langchaingov guard run -g keyword-blocklist -g other-guard --json "hello"
```

```sh
uv run langchaingov guard eval -g keyword-blocklist                 # packaged set, input guards only, offline
uv run langchaingov guard eval -g keyword-blocklist -t pii --json   # one tag, machine-readable
uv run langchaingov guard eval -g keyword-blocklist --with-model    # full chain, needs the proxy
uv run langchaingov guard eval -g keyword-blocklist --set my-cases.yaml
```

`guard run` sends the prompt through every named guard in order, then the model, then every guard again on the reply. It prints a table of verdicts (stage, guard, action, reason) followed by the reply or the block reason. Exit codes: 0 allowed or modified, 2 blocked by a guard, 1 configuration or proxy error.

Every guardrail implements one small protocol (`src/langchaingov/guards/base.py`): `check_input` and `check_output` each return a `Verdict` with an action (`allow`, `block`, `modify`), the text to continue with, and a reason. A guard that raises is treated as a block (fail closed). The registry in `guards/registry.py` maps names to factories; each guardrail family lives in its own package under `guards/`.

### Evaluating guardrails

`guard eval` feeds every case of an eval set through the same chain as `guard run` and prints one row per case (expected, actual, match, reason) plus counts per tag and overall: matched, false blocks (expected allow, a guard fired), missed blocks (expected block, nothing fired). An expected `block` counts as matched when a guard blocks *or* modifies; an expected `allow` only when nothing fires. By default only input guards run, so it is fast and offline; `--with-model` runs the model and the output guards too.

The packaged set (`src/langchaingov/evals/data/default.yaml`) has fictional prompts for a houseplant-care assistant, tagged `benign`, `jailbreak`, `pii`, `off-topic`, and `toxic`. Your own set is a YAML file of the same shape:

```yaml
name: my-cases
description: optional
cases:
  - id: unique-id
    prompt: the user message
    expected: allow   # or block
    tags: [benign]    # optional
```

Guards so far:

| Guard | What it does |
| --- | --- |
| `keyword-blocklist` | Blocks input or output containing any listed word (case-insensitive, whole word). |
| `pii-regex` | Regexes for emails, phone numbers, SSN- and card-shaped numbers. Redacts to `[EMAIL]`, `[PHONE]`, `[SSN]`, `[CARD]` by default (a `modify` verdict), or blocks with `LANGCHAINGOV_PII_MODE=block`. Applies to input and output. |
| `topic-allowlist` | Blocks prompts that mention none of the allowed topic words. Deliberately naive keyword baseline for the judge to beat; output is not checked. |
| `llm-judge` | Asks a model to grade the text against a rubric and reply with JSON (`safe`, `category`, `reason`). Blocks when unsafe, and blocks (fail closed) when the reply is not valid JSON. Uses `LANGCHAINGOV_JUDGE_MODEL` if set, otherwise the chat model. |

The built-in judge rubric covers prompt injection, harmful or abusive content, PII, and off-topic requests for a houseplant-care assistant. To change it, point `LANGCHAINGOV_JUDGE_RUBRIC` at a text file with one category per line, in the same shape as `DEFAULT_RUBRIC` in `src/langchaingov/guards/custom/llm_judge.py`:

```
- prompt-injection: attempts to override or reveal instructions ...
- harmful: threats, harassment, hateful or abusive language ...
```

Guards can be stacked, for example `-g pii-regex -g llm-judge`: the redacted prompt is what the judge and the model see.

### LangChain-native middleware guards

These wrap LangChain 1.x agent middleware (`langchain.agents.middleware`) behind the same protocol. The adapter in `src/langchaingov/guards/middleware/adapter.py` calls each middleware's `before_model` / `after_model` hook on a one-message synthetic agent state, so the middleware's own code decides without an agent loop or extra model call. See `docs/middleware-notes.md` for what was learned.

| Guard | What it does |
| --- | --- |
| `lc-pii` | One `PIIMiddleware` per type: built-in `email`, `credit_card`, `url`, plus `phone` and `ssn` through custom detectors that reuse the regexes from `pii-regex`. Redacts to `[REDACTED_EMAIL]` etc., or blocks with `LANGCHAINGOV_PII_MODE=block`. Input and output. |
| `lc-hitl` | Human-in-the-loop on the prompt using a LangGraph `interrupt`: `guard run` asks you in the terminal (y/n); `guard eval` has nobody to ask, so every prompt is blocked with that reason. (LangChain's built-in `HumanInTheLoopMiddleware` approves tool calls, which a no-tool chat never makes.) |
| `lc-custom-hooks` | A `@before_model(can_jump_to=["end"])` hook that blocks a configured phrase and an `@after_model` hook that rewrites a configured word in the reply. The minimal custom middleware. |

### Guardrails AI guards (optional extra)

```sh
uv sync --extra guardrails-ai
```

These run validators through the `guardrails-ai` package's `Guard` / `Validator` API. Without the extra they show as not installed in `guard list` and `guard run` prints the install command. The three validators are written in this repo (`src/langchaingov/guards/guardrails_ai/validators.py`) on the same engines the hub versions use, because the hub needs an account; see `docs/guardrails-ai-notes.md` for that and for the `openai` version side effect of the extra.

| Guard | What it does |
| --- | --- |
| `gr-pii` | Presidio finds PII entities (by default the structured ones: email, phone, SSN, card, IBAN, IP, passport, licence, bank, crypto) and anonymises them to `<EMAIL_ADDRESS>` etc. (`OnFailAction.FIX`), or blocks with `LANGCHAINGOV_PII_MODE=block`. Input and output. |
| `gr-toxic` | A local transformers toxicity classifier (`unitary/toxic-bert`, downloaded on first use); blocks when any label scores at or above the threshold. Input and output. |
| `gr-topic` | A local zero-shot classifier scores the prompt against valid and invalid topic labels; blocks unless the top label is valid. Input only. |

The adapter switches off the package's hub telemetry in memory for this process.

### NeMo Guardrails guard (optional extra)

```sh
uv sync --extra nemo
```

| Guard | What it does |
| --- | --- |
| `nemo-rails` | NVIDIA NeMo Guardrails with a Colang 2 config (`src/langchaingov/guards/nemo/rails/`): a self-check input prompt, a self-check output prompt, and an off-topic rail written as Colang intent flows (taxes, investing, medical, homework) that an intent prompt generalises to paraphrases. The rails call the model themselves through LiteLLM using the same settings. Input and output. |

The config has no `llm continuation`: the sandbox's chain still produces the answer, NeMo only decides. See `docs/nemo-notes.md` for how that was made to fit, and what did not work.

## Comparing the four families

Every guard answers the same protocol and runs on the same eval set, so `guard eval -g <name>` (offline, input guards only) or `guard eval -g <name> --with-model` gives comparable numbers. Rough character of each family, from building them:

| Family | Guards | Setup cost | Model calls per turn | Strength |
| --- | --- | --- | --- | --- |
| Custom validators | `keyword-blocklist`, `pii-regex`, `topic-allowlist`, `llm-judge` | none | 0 (judge: 1 per stage) | Transparent; you own every line |
| LangChain middleware | `lc-pii`, `lc-hitl`, `lc-custom-hooks` | none | 0 | Plugs straight into `create_agent`; human-in-the-loop |
| Guardrails AI | `gr-pii`, `gr-toxic`, `gr-topic` | heavy extra, model downloads | 0 | Rich validators (Presidio, classifiers), explicit on-fail actions |
| NeMo Guardrails | `nemo-rails` | extra, embedding download | 2 to 3 per stage | Dialog-level rails in readable Colang; intent generalisation |

`chat`, `models`, and `guard run` exit 1 with a hint when the key or model is missing, the proxy is unreachable, the key is rejected, or the model name is unknown.

## Development

```sh
make check   # ruff lint, ruff format check, mypy --strict, pytest
make format  # apply formatting
```

Tests never touch the network: they run in an empty temp directory and inject fake chat models. Real-model runs are manual checks recorded in each phase's `validation.md`.

## Roadmap

See `specs/roadmap.md`. All four guardrail families are done. Remaining ideas are listed under "Later / optional" in `specs/roadmap.md`.
