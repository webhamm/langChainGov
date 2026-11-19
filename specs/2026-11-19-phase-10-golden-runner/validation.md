# Validation — Phase 10: Golden runner

Roadmap: Stage 3 — Golden set drift, phase 10. Branch (created when work starts): `feat/phase-10-golden-runner`. Depends on: phase 09.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-10-golden-runner` can merge once every check below passes.

## 1. Quality gates

- [ ] `make check` passes (lint, format check, strict type check, tests). Lint, format, and mypy pass, and so do 252 tests. The same two NeMo tests that fail on `main` still fail (FastEmbed can't load `all-MiniLM-L6-v2` offline).
- [ ] CI is green on the branch (GitHub Actions billing is still blocked)
- [x] New code has unit tests; no test touches the network (fake chat model, `CharCounter`)

## 2. Behavior

- [x] Every request uses the fixed parameters, and the run header records them (tested)
- [x] Recall scoring is deterministic and matches the table of normalize/answer cases (tested)
- [x] The run file has the header first and one line per case; a run interrupted mid-way still reads back its finished cases (tested)
- [x] A per-case `BadRequestError` is recorded and the run continues (tested)
- [x] Reported prompt tokens far below the estimate sets `suspected_truncation` (tested)
- [x] A non-local or unprofiled model is refused without `--allow-cloud`, and a run over the cap is refused before any request (tested)

## 3. Interfaces

- [x] CLI: `langchaingov golden run`. Table and `--json` output, and exit codes 0/1/4, are covered by tests
- [x] `make_chat_model` keeps its existing behavior for current callers (tested)

## 4. Manual checks

- [x] Real run on the local Llama at all four levels: the run file is written, recall and reported tokens look sane, and no unexpected truncation (logged below)
- [x] Deliberately small `num_ctx` (or a profile that overstates context): the truncation flag or a per-case error appears instead of a silent pass (logged below)

## 5. Docs and specs

- [x] The README covers `golden run`, the run-file format, `--allow-cloud`, and the token cap
- [x] `specs/roadmap.md` marks phase 10 as done
- [x] No real personal data is committed; run files stay git-ignored
- [x] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| 2026-11-19 | 0.9.0 code (header predates the version bump) | `golden run --model llama3.2-3b-32k`, full ladder, seed sent | Recall 100% at L025/L050/L075/L090, finish `stop`, exact `id: answer` format. Reported vs estimated prompt tokens +0.9%/+0.8%/+0.7%/+0.7%. Latency 26 / 44 / 74 / 100 s. Exit 0 | Run by Claude in the session; run `20261119T214340Z-llama3.2-3b-32k` |
| 2026-11-19 | 0.10.0 | `golden run --model llama3.2-3b-32k --context 65536 -l 0.9` (profile overstates a 32k server) | Ollama silently cut 57,482 estimated tokens to 16,386 (half of `num_ctx`). Recall 40%: the model said three needles "aren't mentioned". Flagged `suspected truncation` | The run file also showed `seed_sent: null`: a `--context` override dropped `supports_seed`. Fixed (known profiles keep their flags), with a test |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-10-golden-runner`, ready for review.
