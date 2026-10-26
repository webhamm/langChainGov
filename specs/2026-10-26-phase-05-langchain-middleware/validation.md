# Validation — Phase 05: LangChain-native middleware

Roadmap: Stage 2 — Guardrail families, phase 05. Branch (created when work starts): `feat/phase-05-langchain-middleware`. Depends on: phase 04.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-05-langchain-middleware` can merge once every check below passes.

## 1. Quality gates

- [x] `make check` passes (lint, format check, strict type check, tests)
- [ ] CI is green on the branch
- [x] New code has unit tests; no test makes a network call

## 2. Behavior

- [x] `lc-pii` redacts a fictional email in input and output via the middleware
- [x] `lc-hitl` blocks when the injected policy says block and allows otherwise
- [x] `lc-custom-hooks` blocks on the before-model phrase and rewrites on the after-model phrase

## 3. Interfaces

- [x] CLI: the three guards appear in `guard list` and work with `guard run` and `guard eval`. Covered by tests
- [x] CLI: `guard run --guard lc-hitl` prompts the user interactively in a terminal

## 4. Manual checks

- [ ] `guard run --guard lc-hitl "<prompt>"` with LiteLLM running shows the interrupt and honors the answer (log below)
- [ ] `guard eval --guard lc-pii` completes against the local model (log below)

## 5. Docs and specs

- [x] The README covers the three guards; `docs/middleware-notes.md` exists
- [x] `specs/roadmap.md` marks phase 05 as done
- [x] No real personal data is committed (examples are fictional)
- [x] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| 2026-10-26 | 0.5.0 | `uv run langchaingov guard eval -g lc-pii -g lc-custom-hooks --json` (offline, packaged set, 26 cases) | 13 matched, 0 false blocks, 13 missed: benign 6/6, pii 6/6 (all redacted by PIIMiddleware), jailbreak 1/6 (`developer mode` hook), off-topic 0/4, toxic 0/4. As expected: these guards only target PII and one phrase. | Terminal `lc-hitl` run and the `create_agent` spike against the real model wait on a local model in LiteLLM; CI skipped by decision. |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-05-langchain-middleware`, ready for review.
