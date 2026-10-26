# Validation — Phase 06: Guardrails AI

Roadmap: Stage 2 — Guardrail families, phase 06. Branch (created when work starts): `feat/phase-06-guardrails-ai`. Depends on: phase 05.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-06-guardrails-ai` can merge once every check below passes.

## 1. Quality gates

- [ ] `make check` passes (lint, format check, strict type check, tests)
- [ ] CI is green on the branch
- [ ] New code has unit tests; no test makes a network call; tests needing the extra skip cleanly without it

## 2. Behavior

- [ ] The adapter maps a validator failure to `block` and a fix to `modify`, with reasons
- [ ] `guard list` without the extra shows the guards as not installed and `guard run` on one exits with an install hint

## 3. Interfaces

- [ ] CLI: the chosen guards work with `guard run` and `guard eval` when the extra is installed. Covered by tests with stubs

## 4. Manual checks

- [ ] With the extra installed, `guard eval --guard gr-pii` (and the others) completes against the local model (log below)

## 5. Docs and specs

- [ ] The README covers the extra, setup, and the guards; `docs/guardrails-ai-notes.md` exists
- [ ] `specs/roadmap.md` marks phase 06 as done
- [ ] No real personal data is committed (examples are fictional); no hub token is committed
- [ ] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| | | | | |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-06-guardrails-ai`, ready for review.
