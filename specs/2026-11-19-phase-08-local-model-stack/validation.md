# Validation — Phase 08: Local model stack

Roadmap: Stage 3 — Golden set drift, phase 08. Branch (created when work starts): `feat/phase-08-local-model-stack`. Depends on: phase 07.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-08-local-model-stack` can merge once every check below passes.

## 1. Quality gates

- [ ] `make check` passes (lint, format check, strict type check, tests). Lint, format, and mypy pass, and so do 156 tests, including all 12 new ones. Two NeMo tests (`test_benign_prompt_is_allowed`, `test_off_topic_intent_triggers_colang_refusal`) fail, and they fail the same way on a clean `main`: FastEmbed cannot load `sentence-transformers/all-MiniLM-L6-v2` offline. Not caused by this phase; needs a fix of its own.
- [ ] CI is green on the branch (GitHub Actions billing is still blocked)
- [x] New tests touch no network (config parsing and `bash -n` only)

## 2. Behavior

- [x] The Modelfile `num_ctx`, config `max_input_tokens`, Ollama tag, and `.env.example` model name agree (tested)
- [x] Every script passes `bash -n` (tested)
- [x] `make llm-up` is idempotent: a second run pulls nothing new and reports the proxy already running
- [x] `make llm-up` refuses with a hint when Ollama is unreachable, `.env` lacks `LITELLM_MASTER_KEY`, or `:4000` is held by another process (port case checked on `:4011` while the stack ran on `:4000`)
- [x] No script prints a secret value (the master key appears 0 times in the LiteLLM log or script output)

## 3. Interfaces

- [x] Make targets: `llm-up`, `llm-down`, `llm-status`, `llm-smoke`
- [x] `uv run langchaingov models` lists `llama3.2-3b-32k` while the stack is up (smoke step 1)

## 4. Manual checks

- [x] Cold `make llm-up` (model pull), then `make llm-smoke` passes and `ollama ps` shows context 32768 (logged below)
- [x] `make llm-down` stops the proxy, and `make llm-status` reports it stopped (logged below)

## 5. Docs and specs

- [x] The README covers the local model stack and its make targets
- [x] `specs/roadmap.md` marks phase 08 as done
- [x] No real personal data or secrets are committed
- [x] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| 2026-11-19 | 0.8.0 | Cold `make llm-up` on M3 Pro 18 GB, Ollama 0.40.6, LiteLLM 1.110.1 | Pulled `llama3.2:3b`, built `langchaingov-llama3.2-3b:32k`, LiteLLM live on :4000 | Run by Claude in the session |
| 2026-11-19 | 0.8.0 | `make llm-smoke` | Passed: model listed, chat replied "Yes.", Ollama serves context 32768 (4.2 GB, 100% GPU) | A 3B model doesn't follow "reply with one word: ready" exactly; the smoke test only checks for a non-empty reply |
| 2026-11-19 | 0.8.0 | `make llm-up` again; `OLLAMA_URL=http://localhost:9`; `ENV_FILE` without key; `LLM_PORT=4011` held by `http.server` | Already-running path; three refusals with hints, exit 1 | The first port test exposed a bug (pidfile not keyed by port); fixed by `litellm-<port>.pid` |
| 2026-11-19 | 0.8.0 | `make llm-down`, `make llm-status` | Proxy stopped; status FAIL for LiteLLM, exit 1; Ollama and model still present | |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-08-local-model-stack`, ready for review.
