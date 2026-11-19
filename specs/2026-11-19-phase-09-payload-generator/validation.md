# Validation — Phase 09: Payload generator

Roadmap: Stage 3 — Golden set drift, phase 09. Branch (created when work starts): `feat/phase-09-payload-generator`. Depends on: phase 08.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-09-payload-generator` can merge once every check below passes.

## 1. Quality gates

- [ ] `make check` passes (lint, format check, strict type check, tests). Lint, format, and mypy pass, and so do 207 tests, 51 of them new. The same two NeMo tests that fail on `main` still fail (FastEmbed can't load `all-MiniLM-L6-v2` offline); see phase 08.
- [ ] CI is green on the branch (GitHub Actions billing is still blocked)
- [x] New code has unit tests; no test touches the network (tests use `CharCounter`, never tiktoken's download)

## 2. Behavior

- [x] The same set, seed, counter, and level always produce the same SHA-256 (tested)
- [x] Changing the seed changes the SHA-256 (tested)
- [x] Each payload's estimated tokens is within tolerance of `level × usable context` (tested)
- [x] Every needle appears exactly once, in depth order, near its configured depth, and the question block is last (tested)
- [x] Set-file validation errors are one readable line naming the field (tested)

## 3. Interfaces

- [x] CLI: `langchaingov golden build`. Table output, `--json`, `--dump`, and exit codes 0/1 are covered by tests
- [x] `--model` resolves a profile; `--context` overrides it; an unknown model without `--context` exits 1 with a hint

## 4. Manual checks

- [x] With real tiktoken: `uv run langchaingov golden build --model <local-llama>` twice prints identical hashes, and the 90% rung's estimate is near 90% of the profile's usable context (logged below)

## 5. Docs and specs

- [x] The README covers `golden build` and the golden-set file format
- [x] `specs/roadmap.md` marks phase 09 as done
- [x] No real personal data is committed (needles and filler are fictional)
- [x] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| 2026-11-19 | 0.9.0 | `golden build --model llama3.2-3b-32k --json` twice, real tiktoken `o200k_base` | Identical hashes: L025 `32023a6f6cda`, L050 `5d9ad11b06fd`, L075 `0d2e945286eb`, L090 `b419b075a06a`. L090 is 28,318 of a 28,555 target (31,728 usable) | Run by Claude in the session; the build takes about 1.3 s |
| 2026-11-19 | 0.9.0 | L025 and L090 sent to `llama3.2-3b-32k` via `make llm-up` stack, `max_tokens=1` | Llama reported 7,878 vs tiktoken 7,810 (+0.9%), and 28,505 vs 28,318 (+0.7%). L090 = 87.0% of the 32k window; 19 s and 121 s | Confirms stopping at 90% is safe; the calibration was added to phase 10's context |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-09-payload-generator`, ready for review.
