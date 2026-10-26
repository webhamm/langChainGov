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

## Commands

```sh
uv run langchaingov models                      # what the proxy exposes; pick one for LANGCHAINGOV_MODEL
uv run langchaingov chat "Say hello in five words"
uv run langchaingov chat --system "You are terse." --model other-model --json "hi"
uv run langchaingov version
```

`chat` and `models` exit 1 with a hint when the key or model is missing, the proxy is unreachable, the key is rejected, or the model name is unknown.

## Development

```sh
make check   # ruff lint, ruff format check, mypy --strict, pytest
make format  # apply formatting
```

Tests never touch the network: they run in an empty temp directory and inject fake chat models. Real-model runs are manual checks recorded in each phase's `validation.md`.

## Roadmap

See `specs/roadmap.md`. Next up after this scaffold: the guardrail core (protocol, registry, chain) and an eval harness, then one phase per guardrail family (custom validators, LangChain middleware, Guardrails AI, NeMo Guardrails).
