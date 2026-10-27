# Validation — Phase 07: NeMo Guardrails

Roadmap: Stage 2 — Guardrail families, phase 07. Branch (created when work starts): `feat/phase-07-nemo-guardrails`. Depends on: phase 06.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-07-nemo-guardrails` can merge once every check below passes.

## 1. Quality gates

- [x] `make check` passes (lint, format check, strict type check, tests)
- [ ] CI is green on the branch
- [x] New code has unit tests; no test makes a network call; tests needing the extra skip cleanly without it

## 2. Behavior

- [x] The adapter maps a rail refusal to `block` with the rail's reason and a normal reply to `allow`
- [x] The `rails/` config loads without error when the extra is installed

## 3. Interfaces

- [x] CLI: `nemo-rails` works with `guard run` and `guard eval` when the extra is installed. Covered by tests with stubs

## 4. Manual checks

- [ ] With the extra installed and a local model in LiteLLM, `guard eval --guard nemo-rails --with-model` completes and the summary is logged below with comparison notes (user run)

## 5. Docs and specs

- [x] The README covers the extra, setup, the guard, and the four-family comparison; `docs/nemo-notes.md` exists
- [x] `specs/roadmap.md` marks phase 07 as done
- [x] No real personal data is committed (examples are fictional)
- [x] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| 2026-10-26 | 0.7.0 | `make check` with both extras; `uv sync` (core only) then `pytest`; NeMo adapter exercised through a fake `LLMModel` answering the self-check and intent prompts | Both extras: 146 passed. Core only: 126 passed, 2 skipped (the Guardrails AI and NeMo directories). Fake-model paths covered: benign allow, self-check input block, paraphrased off-topic prompt refused via Colang intent flow, output rail block and allow. | Real `nemo-rails` run waits on a local model in LiteLLM (the rails call it directly); CI skipped by decision. |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-07-nemo-guardrails`, ready for review.
