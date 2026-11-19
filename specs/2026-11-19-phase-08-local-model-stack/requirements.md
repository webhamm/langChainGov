# Requirements — Phase 08: Local model stack

Roadmap: Stage 3 — Golden set drift, phase 08. Branch (created when work starts): `feat/phase-08-local-model-stack`. Depends on: phase 07.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

## Goal

`make llm-up` stands up a light local Llama (`llama3.2:3b`, served with a 32k context window) behind a repo-owned LiteLLM proxy on `:4000`, so `langchaingov chat`, the guards, and the golden set have a real local model without Docker or the shared proxy repo.

## Scope

### In scope

- **Ollama Modelfile** `infra/ollama/llama3.2-3b-32k.Modelfile`: `FROM llama3.2:3b` with `PARAMETER num_ctx 32768`. Built as the tag `langchaingov-llama3.2-3b:32k`. The served window is in version control rather than in Ollama's global defaults, and other models on the machine are untouched.
- **LiteLLM config** `infra/litellm/config.yaml`: one model, `llama3.2-3b-32k`, mapping to `ollama_chat/langchaingov-llama3.2-3b:32k` at `http://localhost:11434`, with `model_info.max_input_tokens: 32768`. The master key comes from `os.environ/LITELLM_MASTER_KEY` (already in `.env`, and already accepted by `Settings`).
- **LiteLLM run method**: `uvx --env-file .env --from 'litellm[proxy]==1.110.1' litellm --config infra/litellm/config.yaml --port 4000`. The version is pinned, it's isolated from the project venv, and no Docker is needed. It runs in the background with its pid and log in `.run/` (git-ignored).
- **Scripts** in `scripts/llm/` (bash, `set -euo pipefail`, commented for reading):
  - `lib.sh`: shared defaults (`OLLAMA_URL`, `LLM_PORT`, base model, tag, Modelfile, config, LiteLLM version), log/die helpers, and a check for a running proxy via its pidfile.
  - `up.sh`: idempotent. Checks Ollama is reachable (hints `brew services start ollama` if not), pulls `llama3.2:3b` if missing, (re)creates the tag from the Modelfile, checks `.env` has `LITELLM_MASTER_KEY` (by name only; values are never printed), refuses if `:4000` is held by another process, starts LiteLLM, and waits for `/health/liveliness`.
  - `down.sh`: stops the LiteLLM it started (by pidfile). Leaves the Ollama service and models alone.
  - `status.sh`: Ollama version and reachability, base model and tag present, loaded models with served context (`ollama ps`), and the proxy's pid, port, and liveness.
  - `smoke.sh`: `langchaingov models` lists `llama3.2-3b-32k`, `langchaingov chat --model llama3.2-3b-32k` returns text, and `ollama ps` shows the tag loaded with context 32768.
- **Makefile** targets `llm-up`, `llm-down`, `llm-status`, `llm-smoke`. Port and URLs can be overridden with environment variables.
- **`.env.example`**: `LANGCHAINGOV_MODEL=llama3.2-3b-32k` and a `LITELLM_MASTER_KEY` line for the repo-owned proxy.
- **Tests** in `tests/test_llm_stack.py`, no network: the Modelfile's `num_ctx` equals the config's `max_input_tokens`; the config's Ollama tag equals the tag in `lib.sh`; `.env.example`'s model equals the config's `model_name`; every script passes `bash -n`.

### Out of scope

- Cloud models in the repo-owned proxy. The shared `si-agent-platform-proxy` stays the place for those; golden-set `--allow-cloud` (phase 10) can point at it.
- A second, larger local model (e.g. `llama3.1:8b`), KV-cache quantization, and other Ollama tuning ("Later / optional").
- Starting or configuring the Ollama service itself (Homebrew already runs it).
- A direct `langchain-ollama` backend (still in "Later / optional").

## Open questions

- Which light model should the stack serve? **Resolved:** `llama3.2:3b`. About 2 GB, 128k advertised context, and leaves the most of the 18 GB for a long served window.
- How should langchaingov reach the Ollama model? **Resolved:** a repo-owned LiteLLM config started with `uvx` on `:4000`, using the existing `LITELLM_MASTER_KEY`. No Docker, and the tech stack's "everything through LiteLLM" stays true.
- How large a context window should it serve? **Resolved:** 32k (`num_ctx 32768`), set in a versioned Modelfile and built as its own tag.
- What form should the stand-up scripts take? **Resolved:** Makefile targets wrapping small bash scripts in `scripts/llm/`.

## Context

- `tech-stack.md` → Model endpoint: everything goes through LiteLLM's OpenAI-compatible API; `llm.py` stays the only model client.
- `mission.md` principle 1: local first. This phase is what makes it true on this machine.
- `mission.md` principle 4: tests never touch the network; real stand-up runs are manual checks logged in `validation.md`.
- Phase 09: the golden set's first model profile is `llama3.2-3b-32k` with `context_tokens: 32768`, `local: true`.
