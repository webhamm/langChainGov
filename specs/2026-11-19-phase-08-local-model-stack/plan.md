# Plan — Phase 08: Local model stack

Roadmap: Stage 3 — Golden set drift, phase 08. Branch (created when work starts): `feat/phase-08-local-model-stack`. Depends on: phase 07.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

See `requirements.md` for scope and decisions, and `validation.md` for the merge bar.

## 1. Branch

1.1. Create `feat/phase-08-local-model-stack` from `main`, with phase 07 merged.

## 2. Configs

2.1. `infra/ollama/llama3.2-3b-32k.Modelfile`.
2.2. `infra/litellm/config.yaml`.
2.3. `.env.example`: model name and master key line. `.gitignore`: `.run/`.

## 3. Scripts

3.1. `scripts/llm/lib.sh`, `up.sh`, `down.sh`, `status.sh`, `smoke.sh`.
3.2. Makefile targets `llm-up`, `llm-down`, `llm-status`, `llm-smoke`.
3.3. `tests/test_llm_stack.py`: config consistency and `bash -n` for every script.

## 4. Stand it up

4.1. `make llm-up` from cold (pulls the model), `make llm-smoke`, `make llm-status`, `make llm-down`, then `make llm-up` again to confirm it's idempotent. Log the results in `validation.md`.

## 5. Wrap-up

5.1. Bump the version to 0.8.0 (`pyproject.toml` and `langchaingov.__version__`).
5.2. Update the README: a "Local model stack" section with the make targets and requirements (Homebrew Ollama, uv).
5.3. Mark phase 08 done in `specs/roadmap.md`.
5.4. Work through `validation.md` and record the results.
