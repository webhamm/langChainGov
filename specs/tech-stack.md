# Tech stack

## Choices

| Concern | Choice | Notes |
| --- | --- | --- |
| Language | Python 3.12 (pinned in `.python-version`, installed by uv) | 3.15 is on the machine, but guardrail libraries lag on new interpreters. uv manages the interpreter. |
| Packaging | uv, `src/` layout, `pyproject.toml` | `uv sync` installs everything; `uv run langchaingov ...` runs the CLI. |
| LLM framework | `langchain` 1.x, `langchain-openai` | LiteLLM exposes an OpenAI-compatible API, so `ChatOpenAI(base_url=..., api_key=...)` is the only model client. |
| Model endpoint | Local LiteLLM proxy at `http://localhost:4000/v1` | Fronts the local Llama. Requires an API key (`LITELLM_API_KEY` or `LITELLM_MASTER_KEY`). Model name is a setting (`LANGCHAINGOV_MODEL`). |
| Local model stack | Homebrew Ollama serving `llama3.2:3b` as tag `langchaingov-llama3.2-3b:32k` (`infra/ollama/*.Modelfile`, `num_ctx 32768`); repo-owned LiteLLM config `infra/litellm/config.yaml` run by `uvx` with a pinned `litellm[proxy]` | `make llm-up / llm-down / llm-status / llm-smoke` wrap `scripts/llm/*.sh`. No Docker. LiteLLM model name `llama3.2-3b-32k`. |
| Config | `pydantic-settings`, env vars with `LANGCHAINGOV_` prefix, optional `.env` | `.env` is git-ignored; `.env.example` is committed. |
| CLI | `typer` + `rich` | Subcommands: `chat`, `guard list`, `guard run`, `guard eval`, and (Stage 3) `golden build`, `golden run`, `golden runs`, `golden baseline`, `golden compare`. `--json` on every command for machine-readable output. |
| Token counting | `tiktoken` (`o200k_base`) behind a `TokenCounter` protocol | Offline and approximate for non-OpenAI models; the model's reported `prompt_tokens` is recorded on every run to calibrate. Tests inject a character-based fake counter, because tiktoken downloads its encoding on first use. |
| Golden-set run history | One JSONL file per run under `runs/golden/` (git-ignored, `LANGCHAINGOV_RUNS_DIR`) | Line 1 is the run header, then one line per case, appended as each case finishes so a crashed run keeps partial results. Prompts are not stored, only their SHA-256: payloads regenerate from the seed. |
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

## Golden-set drift (Stage 3)

```
 golden/data/default.yaml          golden/models.yaml
 (seed, needles, fill levels)      (model ──► context_tokens, local)
            │                                │
            ▼                                ▼
 ┌──────────────────────────────────────────────────────┐
 │ generator: seeded filler + needles at fixed depths    │──► golden build  (stats only)
 │ sized by TokenCounter to level × (context − reserve)  │
 └──────────────────────────┬───────────────────────────┘
                            │ Payload(prompt, sha256, est_tokens, needles)
 ┌──────────────────────────▼───────────────────────────┐
 │ runner: fixed params (temperature 0, seed, max_tokens)│──► make_chat_model ──► LiteLLM
 │ captures text, usage, finish_reason, latency, score   │
 └──────────────────────────┬───────────────────────────┘
                            │ appends CaseResult
              runs/golden/<run_id>.jsonl ◄── golden runs / golden baseline
                            │
 ┌──────────────────────────▼───────────────────────────┐
 │ compare: run vs baseline per fill level ──► recall Δ, │──► golden compare (exit 3 on drift)
 │ difflib similarity, length Δ, latency Δ, thresholds   │
 └──────────────────────────────────────────────────────┘
```

- The golden set lives in `src/langchaingov/golden/` and measures the raw model, so the runner calls the chat model from `make_chat_model` directly instead of `GuardedChain`, so it can read `usage_metadata` and `finish_reason`. Running the golden set through guards is a later option.
- Generation is pure and deterministic: the same set file, seed, counter, and target size always give the same prompt bytes and the same SHA-256. Any change to the generator that changes bytes bumps the set's `generator_version`, and compare refuses to compare across versions.
- Scoring is deterministic too: a needle counts as recalled when its normalized expected answer appears in the response. No LLM judge, so the measurement never drifts on its own.
