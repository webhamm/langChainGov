# Validation — Phase 02: Guardrail core

Roadmap: Stage 1 — Foundation, phase 02. Branch (created when work starts): `feat/phase-02-guardrail-core`. Depends on: phase 01.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-02-guardrail-core` can merge once every check below passes.

## 1. Quality gates

- [ ] `make check` passes (lint, format check, strict type check, tests)
- [ ] CI is green on the branch
- [ ] New code has unit tests; no test makes a network call

## 2. Behavior

- [ ] `GuardedChain` stops at the first input `block` and never calls the model
- [ ] `GuardedChain` threads `modify` text into the model call and into later guards
- [ ] `GuardedChain` runs output checks on the model reply and reports a block there
- [ ] A guard that raises is handled per the resolved fail-open/fail-closed decision, with a test
- [ ] `keyword-blocklist` blocks a prompt containing a listed word and allows one that does not

## 3. Interfaces

- [ ] CLI: `langchaingov guard list` prints every registered guard
- [ ] CLI: `langchaingov guard run --guard <name> "<prompt>" [--json]`. Output modes and exit codes are covered by tests

## 4. Manual checks

- [ ] With LiteLLM running, `guard run --guard keyword-blocklist` answers a benign prompt and blocks one containing a listed word (log below)

## 5. Docs and specs

- [ ] The README covers `guard list` and `guard run`
- [ ] `specs/roadmap.md` marks phase 02 as done
- [ ] No real personal data is committed (examples are fictional)
- [ ] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| | | | | |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-02-guardrail-core`, ready for review.
