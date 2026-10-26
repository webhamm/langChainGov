# Validation — Phase 01: Scaffold and chat

Roadmap: Stage 1 — Foundation, phase 01. Branch (created when work starts): `feat/phase-01-scaffold-and-chat`. Depends on: none.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-01-scaffold-and-chat` can merge once every check below passes.

## 1. Quality gates

- [ ] `make check` passes (lint, format check, strict type check, tests)
- [ ] CI is green on the branch
- [ ] New code has unit tests; no test makes a network call

## 2. Behavior

- [ ] `Settings()` reads base URL, model, key, and temperature from env, with the documented defaults
- [ ] `make_chat_model` returns a `ChatOpenAI` configured with the settings' base URL and model
- [ ] `chat` with a fake model prints the fake's reply and exits 0
- [ ] `chat` exits 1 with a hint when the model raises a connection or auth error

## 3. Interfaces

- [ ] CLI: `langchaingov chat "<prompt>" [--system] [--model] [--json]`. Output modes and exit codes are covered by tests
- [ ] CLI: `langchaingov version` prints the package version

## 4. Manual checks

- [ ] With LiteLLM running and `.env` set, `uv run langchaingov chat "Say hello in five words"` returns a reply from the local Llama (log below)

## 5. Docs and specs

- [ ] The README covers setup and the `chat` and `version` commands
- [ ] `specs/roadmap.md` marks phase 01 as done
- [ ] No real personal data is committed (`.env` ignored, examples are fictional)
- [ ] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| | | | | |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-01-scaffold-and-chat`, ready for review.
