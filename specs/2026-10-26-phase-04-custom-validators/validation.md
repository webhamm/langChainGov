# Validation — Phase 04: Custom validators

Roadmap: Stage 2 — Guardrail families, phase 04. Branch (created when work starts): `feat/phase-04-custom-validators`. Depends on: phase 03.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-04-custom-validators` can merge once every check below passes.

## 1. Quality gates

- [ ] `make check` passes (lint, format check, strict type check, tests)
- [ ] CI is green on the branch
- [ ] New code has unit tests; no test makes a network call

## 2. Behavior

- [ ] `pii-regex` redacts a fictional email, phone, and SSN and leaves clean text untouched
- [ ] `topic-allowlist` blocks an off-topic prompt and allows an on-topic one
- [ ] `llm-judge` blocks when the (fake) model says unsafe, allows when safe, and blocks on malformed output

## 3. Interfaces

- [ ] CLI: `guard list` shows the three new guards; `guard run` and `guard eval` accept them. Covered by tests

## 4. Manual checks

- [ ] `guard eval --guard llm-judge` against the local model completes and the summary is logged below with observations on judge quality

## 5. Docs and specs

- [ ] The README covers the three guards and their settings
- [ ] `specs/roadmap.md` marks phase 04 as done
- [ ] No real personal data is committed (PII examples are fictional)
- [ ] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| | | | | |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-04-custom-validators`, ready for review.
