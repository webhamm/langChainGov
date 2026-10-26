# Validation — Phase 05: LangChain-native middleware

Roadmap: Stage 2 — Guardrail families, phase 05. Branch (created when work starts): `feat/phase-05-langchain-middleware`. Depends on: phase 04.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-05-langchain-middleware` can merge once every check below passes.

## 1. Quality gates

- [ ] `make check` passes (lint, format check, strict type check, tests)
- [ ] CI is green on the branch
- [ ] New code has unit tests; no test makes a network call

## 2. Behavior

- [ ] `lc-pii` redacts a fictional email in input and output via the middleware
- [ ] `lc-hitl` blocks when the injected policy says block and allows otherwise
- [ ] `lc-custom-hooks` blocks on the before-model phrase and rewrites on the after-model phrase

## 3. Interfaces

- [ ] CLI: the three guards appear in `guard list` and work with `guard run` and `guard eval`. Covered by tests
- [ ] CLI: `guard run --guard lc-hitl` prompts the user interactively in a terminal

## 4. Manual checks

- [ ] `guard run --guard lc-hitl "<prompt>"` with LiteLLM running shows the interrupt and honors the answer (log below)
- [ ] `guard eval --guard lc-pii` completes against the local model (log below)

## 5. Docs and specs

- [ ] The README covers the three guards; `docs/middleware-notes.md` exists
- [ ] `specs/roadmap.md` marks phase 05 as done
- [ ] No real personal data is committed (examples are fictional)
- [ ] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| | | | | |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-05-langchain-middleware`, ready for review.
