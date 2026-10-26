# Validation — Phase 02: Guardrail core

Roadmap: Stage 1 — Foundation, phase 02. Branch (created when work starts): `feat/phase-02-guardrail-core`. Depends on: phase 01.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-02-guardrail-core` can merge once every check below passes.

## 1. Quality gates

- [x] `make check` passes (lint, format check, strict type check, tests)
- [ ] CI is green on the branch
- [x] New code has unit tests; no test makes a network call

## 2. Behavior

- [x] `GuardedChain` stops at the first input `block` and never calls the model
- [x] `GuardedChain` threads `modify` text into the model call and into later guards
- [x] `GuardedChain` runs output checks on the model reply and reports a block there
- [x] A guard that raises is handled per the resolved fail-open/fail-closed decision, with a test
- [x] `keyword-blocklist` blocks a prompt containing a listed word and allows one that does not

## 3. Interfaces

- [x] CLI: `langchaingov guard list` prints every registered guard
- [x] CLI: `langchaingov guard run --guard <name> "<prompt>" [--json]`. Output modes and exit codes are covered by tests

## 4. Manual checks

- [ ] With LiteLLM running, `guard run --guard keyword-blocklist` answers a benign prompt and blocks one containing a listed word (log below)

## 5. Docs and specs

- [x] The README covers `guard list` and `guard run`
- [x] `specs/roadmap.md` marks phase 02 as done
- [x] No real personal data is committed (examples are fictional)
- [x] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| 2026-10-26 | 0.2.0 | (manual check pending: no local model configured yet; CI skipped by decision until GitHub billing is fixed) | | |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-02-guardrail-core`, ready for review.
