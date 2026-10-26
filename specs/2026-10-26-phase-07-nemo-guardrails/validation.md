# Validation — Phase 07: NeMo Guardrails

Roadmap: Stage 2 — Guardrail families, phase 07. Branch (created when work starts): `feat/phase-07-nemo-guardrails`. Depends on: phase 06.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-07-nemo-guardrails` can merge once every check below passes.

## 1. Quality gates

- [ ] `make check` passes (lint, format check, strict type check, tests)
- [ ] CI is green on the branch
- [ ] New code has unit tests; no test makes a network call; tests needing the extra skip cleanly without it

## 2. Behavior

- [ ] The adapter maps a rail refusal to `block` with the rail's reason and a normal reply to `allow`
- [ ] The `rails/` config loads without error when the extra is installed

## 3. Interfaces

- [ ] CLI: `nemo-rails` works with `guard run` and `guard eval` when the extra is installed. Covered by tests with stubs

## 4. Manual checks

- [ ] With the extra installed and LiteLLM running, `guard eval --guard nemo-rails` completes and the summary is logged below with comparison notes

## 5. Docs and specs

- [ ] The README covers the extra, setup, the guard, and the four-family comparison; `docs/nemo-notes.md` exists
- [ ] `specs/roadmap.md` marks phase 07 as done
- [ ] No real personal data is committed (examples are fictional)
- [ ] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| | | | | |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-07-nemo-guardrails`, ready for review.
