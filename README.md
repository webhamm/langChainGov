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

`chat`, `models`, and `guard run` exit 1 with a hint when the key or model is missing, the proxy is unreachable, the key is rejected, or the model name is unknown.

## Development

```sh
make check   # ruff lint, ruff format check, mypy --strict, pytest
make format  # apply formatting
```

Tests never touch the network: they run in an empty temp directory and inject fake chat models. Real-model runs are manual checks recorded in each phase's `validation.md`.

## Roadmap

See `specs/roadmap.md`. Next up: then one phase per guardrail family (custom validators, LangChain middleware, Guardrails AI, NeMo Guardrails).
