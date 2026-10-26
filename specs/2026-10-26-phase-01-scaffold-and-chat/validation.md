# Validation — Phase 01: Scaffold and chat

Roadmap: Stage 1 — Foundation, phase 01. Branch (created when work starts): `feat/phase-01-scaffold-and-chat`. Depends on: none.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-01-scaffold-and-chat` can merge once every check below passes.

## 1. Quality gates

- [x] `make check` passes (lint, format check, strict type check, tests)
- [ ] CI is green on the branch
- [x] New code has unit tests; no test makes a network call

## 2. Behavior

- [x] `Settings()` reads base URL, model, key, and temperature from env, with the documented defaults
- [x] `make_chat_model` returns a `ChatOpenAI` configured with the settings' base URL and model
- [x] `chat` with a fake model prints the fake's reply and exits 0
- [x] `chat` exits 1 with a hint when the model raises a connection or auth error

## 3. Interfaces

- [x] CLI: `langchaingov chat "<prompt>" [--system] [--model] [--json]`. Output modes and exit codes are covered by tests
- [x] CLI: `langchaingov version` prints the package version
- [x] CLI: `langchaingov models [--json]` lists the proxy's models; key check and errors covered by tests

## 4. Manual checks

- [ ] With LiteLLM running and `.env` set, `uv run langchaingov chat "Say hello in five words"` returns a reply from the local Llama (log below)

## 5. Docs and specs

- [x] The README covers setup and the `chat`, `models`, and `version` commands
- [x] `specs/roadmap.md` marks phase 01 as done
- [x] No real personal data is committed (`.env` ignored, examples are fictional)
- [x] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| 2026-10-26 | 0.1.0 | `uv run langchaingov models` against the local LiteLLM proxy, key from the existing `.env` | Exit 0; listed claude-haiku-4-5, claude-opus-5, claude-sonnet-5, gpt-4o-mini-transcribe, text-embedding-3-small. No Llama model is exposed. | Chat manual check waits on the model choice. |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-01-scaffold-and-chat`, ready for review.
