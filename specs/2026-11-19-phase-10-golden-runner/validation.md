# Validation — Phase 10: Golden runner

Roadmap: Stage 3 — Golden set drift, phase 10. Branch (created when work starts): `feat/phase-10-golden-runner`. Depends on: phase 09.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-10-golden-runner` can merge once every check below passes.

## 1. Quality gates

- [ ] `make check` passes (lint, format check, strict type check, tests)
- [ ] CI is green on the branch
- [ ] New code has unit tests; no test touches the network (fake chat model, `CharCounter`)

## 2. Behavior

- [ ] Every request uses the fixed parameters, and the run header records them (tested)
- [ ] Recall scoring is deterministic and matches the table of normalize/answer cases (tested)
- [ ] The run file has the header first and one line per case; a run interrupted mid-way still reads back its finished cases (tested)
- [ ] A per-case `BadRequestError` is recorded and the run continues (tested)
- [ ] Reported prompt tokens far below the estimate sets `suspected_truncation` (tested)
- [ ] A non-local or unprofiled model is refused without `--allow-cloud`, and a run over the cap is refused before any request (tested)

## 3. Interfaces

- [ ] CLI: `langchaingov golden run`. Table and `--json` output, and exit codes 0/1/4, are covered by tests
- [ ] `make_chat_model` keeps its existing behavior for current callers (tested)

## 4. Manual checks

- [ ] Real run on the local Llama at all four levels: the run file is written, recall and reported tokens look sane, and no unexpected truncation (logged below)
- [ ] Deliberately small `num_ctx` (or a profile that overstates context): the truncation flag or a per-case error appears instead of a silent pass (logged below)

## 5. Docs and specs

- [ ] The README covers `golden run`, the run-file format, `--allow-cloud`, and the token cap
- [ ] `specs/roadmap.md` marks phase 10 as done
- [ ] No real personal data is committed; run files stay git-ignored
- [ ] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| | | | | |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-10-golden-runner`, ready for review.
