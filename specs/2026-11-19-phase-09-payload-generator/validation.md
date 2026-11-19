# Validation — Phase 09: Payload generator

Roadmap: Stage 3 — Golden set drift, phase 09. Branch (created when work starts): `feat/phase-09-payload-generator`. Depends on: phase 08.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-09-payload-generator` can merge once every check below passes.

## 1. Quality gates

- [ ] `make check` passes (lint, format check, strict type check, tests)
- [ ] CI is green on the branch
- [ ] New code has unit tests; no test touches the network (tests use `CharCounter`, never tiktoken's download)

## 2. Behavior

- [ ] The same set, seed, counter, and level always produce the same SHA-256 (tested)
- [ ] Changing the seed changes the SHA-256 (tested)
- [ ] Each payload's estimated tokens is within tolerance of `level × usable context` (tested)
- [ ] Every needle appears exactly once, in depth order, near its configured depth, and the question block is last (tested)
- [ ] Set-file validation errors are one readable line naming the field (tested)

## 3. Interfaces

- [ ] CLI: `langchaingov golden build`. Table output, `--json`, `--dump`, and exit codes 0/1 are covered by tests
- [ ] `--model` resolves a profile; `--context` overrides it; an unknown model without `--context` exits 1 with a hint

## 4. Manual checks

- [ ] With real tiktoken: `uv run langchaingov golden build --model <local-llama>` twice prints identical hashes, and the 90% rung's estimate is near 90% of the profile's usable context (logged below)

## 5. Docs and specs

- [ ] The README covers `golden build` and the golden-set file format
- [ ] `specs/roadmap.md` marks phase 09 as done
- [ ] No real personal data is committed (needles and filler are fictional)
- [ ] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| | | | | |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-09-payload-generator`, ready for review.
