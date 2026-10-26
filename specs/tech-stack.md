# Tech stack

## Choices

| Concern | Choice | Notes |
| --- | --- | --- |
| Language | Python 3.12 (pinned in `.python-version`, installed by uv) | 3.15 is on the machine, but guardrail libraries lag on new interpreters. uv manages the interpreter. |
| Packaging | uv, `src/` layout, `pyproject.toml` | `uv sync` installs everything; `uv run langchaingov ...` runs the CLI. |
| LLM framework | `langchain` 1.x, `langchain-openai` | LiteLLM exposes an OpenAI-compatible API, so `ChatOpenAI(base_url=..., api_key=...)` is the only model client. |
| Model endpoint | Local LiteLLM proxy at `http://localhost:4000/v1` | Fronts the local Llama. Requires an API key (`LITELLM_API_KEY`). Model name is a setting (`LANGCHAINGOV_MODEL`). |
| Config | `pydantic-settings`, env vars with `LANGCHAINGOV_` prefix, optional `.env` | `.env` is git-ignored; `.env.example` is committed. |
| CLI | `typer` + `rich` | Subcommands: `chat`, `guard list`, `guard run`, `guard eval`. `--json` on every command for machine-readable output. |
| Guardrail libraries | `guardrails-ai`, `nemoguardrails` as optional extras | Installed only in their phases via `uv sync --extra guardrails-ai` etc., so the core stays light. |
| Tests | `pytest`, `langchain_core.language_models.fake_chat_models` | No network in tests. Real-model runs are manual checks. |
| Quality | `ruff` (lint + format), `mypy --strict`, `make check` | `make check` = ruff check, ruff format --check, mypy, pytest. |
| CI | GitHub Actions on push and PR | Runs `make check` on Python 3.12. |
| Versioning | `version` in `pyproject.toml` and `langchaingov.__version__` | Both must match; bumped every phase. |

## Architecture

```
                 ┌──────────────────────────────────────────────┐
                 │  langchaingov CLI (typer)                     │
                 │  chat │ guard list │ guard run │ guard eval   │
                 └───────────────┬──────────────────────────────┘
                                 │
                 ┌───────────────▼──────────────────────────────┐
                 │  GuardedChain                                 │
                 │   input ──► [Guardrail.check_input] ──┐       │
                 │                                       ▼       │
                 │                               ChatOpenAI ───► LiteLLM :4000 ───► local Llama
                 │                                       │       │
                 │   output ◄── [Guardrail.check_output] ◄┘      │
                 └───────────────┬──────────────────────────────┘
                                 │  Verdict(action, reason, text)
                 ┌───────────────▼──────────────────────────────┐
                 │  Guardrail registry (name ──► factory)        │
                 ├──────────────┬──────────────┬────────────────┤
                 │ guards/      │ guards/      │ guards/        │
                 │ custom/      │ middleware/  │ guardrails_ai/ │ guards/nemo/
                 │ regex, PII,  │ LangChain    │ hub validators │ Colang rails
                 │ LLM judge    │ middleware   │                │
                 └──────────────┴──────────────┴────────────────┘
                                 ▲
                 evals/*.yaml ───┘  (guard eval feeds cases through the same path)
```

## The core pattern

Everything is a `Guardrail`:

```python
class Verdict(BaseModel):
    action: Literal["allow", "block", "modify"]
    reason: str          # human-readable, always set when action != allow
    text: str            # the (possibly modified) text to continue with
    guard: str           # name of the guardrail that produced this verdict

class Guardrail(Protocol):
    name: str
    def check_input(self, text: str) -> Verdict: ...
    def check_output(self, text: str) -> Verdict: ...
```

- A guardrail family is a package under `src/langchaingov/guards/` that registers one or more named guardrails with the registry.
- `GuardedChain` takes a model and a list of guardrails. It runs every `check_input`, stops at the first `block`, passes modified text onward, calls the model, then runs every `check_output` the same way. It returns a `GuardedResult` with the final text and the list of verdicts.
- The CLI and the eval harness only ever talk to `GuardedChain` and the registry. Third-party libraries are wrapped behind the protocol in their own package and never leak into the CLI.
- Guardrails that need the model (LLM-as-judge, NeMo) receive the same `ChatOpenAI` instance so there is one place that knows about LiteLLM.
