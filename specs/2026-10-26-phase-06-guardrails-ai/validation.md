# Validation — Phase 06: Guardrails AI

Roadmap: Stage 2 — Guardrail families, phase 06. Branch (created when work starts): `feat/phase-06-guardrails-ai`. Depends on: phase 05.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-06-guardrails-ai` can merge once every check below passes.

## 1. Quality gates

- [x] `make check` passes (lint, format check, strict type check, tests)
- [ ] CI is green on the branch
- [x] New code has unit tests; no test makes a network call; tests needing the extra skip cleanly without it

## 2. Behavior

- [x] The adapter maps a validator failure to `block` and a fix to `modify`, with reasons
- [x] `guard list` without the extra shows the guards as not installed and `guard run` on one exits with an install hint

## 3. Interfaces

- [x] CLI: the chosen guards work with `guard run` and `guard eval` when the extra is installed. Covered by tests with stubs

## 4. Manual checks

- [x] With the extra installed, `guard eval --guard gr-pii` completes offline with real Presidio (log below)
- [ ] `guard eval --guard gr-toxic` and `--guard gr-topic` complete after the classifier weights download (user run; needs network for the first run)

## 5. Docs and specs

- [x] The README covers the extra, setup, and the guards; `docs/guardrails-ai-notes.md` exists
- [x] `specs/roadmap.md` marks phase 06 as done
- [x] No real personal data is committed (examples are fictional); no hub token is committed
- [x] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| 2026-10-26 | 0.6.0 | `uv run langchaingov guard eval -g gr-pii --json` (offline, real Presidio + en_core_web_sm, packaged set, 26 cases) | 12 matched, 0 false blocks, 14 missed: benign 6/6, pii 6/6 (all anonymised), jailbreak/off-topic/toxic 0 (not this guard's job). With Presidio's default entity set the same run had 1 false block (`winter` as DATE_TIME) and rewrote jailbreak prompts (`Summarise`, `Ignorez` as PERSON), which is why the default entity list is now the structured identifiers only. | Core-only install: 125 passed, 1 skipped (the Guardrails directory). `gr-toxic` / `gr-topic` real runs wait on the classifier downloads; CI skipped by decision. |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-06-guardrails-ai`, ready for review.
