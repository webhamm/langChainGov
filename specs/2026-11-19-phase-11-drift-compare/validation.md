# Validation — Phase 11: Drift compare

Roadmap: Stage 3 — Golden set drift, phase 11. Branch (created when work starts): `feat/phase-11-drift-compare`. Depends on: phase 10.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-11-drift-compare` can merge once every check below passes.

## 1. Quality gates

- [ ] `make check` passes (lint, format check, strict type check, tests)
- [ ] CI is green on the branch
- [ ] New code has unit tests; no test touches the network (comparison works on fixture run files)

## 2. Behavior

- [ ] Runs with a different set hash, `generator_version`, or prompt hash are reported "not comparable" with the reason, never as drift (tested)
- [ ] A different model is refused without `--cross-model` (tested)
- [ ] Each drift rule fires just past its threshold and not at it, and the flag names the metric, value, and threshold (tested)
- [ ] A prompt-token change is reported as an environment warning, not drift (tested)
- [ ] `golden runs` shows complete, partial, and errored runs correctly; only complete runs can be pinned (tested)

## 3. Interfaces

- [ ] CLI: `golden runs`, `golden baseline`, `golden compare`. Text and `--json` output, and exit codes 0/1/3, are covered by tests

## 4. Manual checks

- [ ] End-to-end MVP on the local Llama: `golden run`, `golden baseline <id>`, `golden run` again, `golden compare` reports STABLE (or explains the drift it found) (logged below)
- [ ] Induced drift: rerun with a changed parameter (e.g. temperature 1 via settings) and confirm `golden compare` reports DRIFT and exits 3 (logged below)

## 5. Docs and specs

- [ ] The README has the MVP runbook and explains the drift table
- [ ] `specs/roadmap.md` marks phase 11 as done
- [ ] No real personal data is committed (fixture runs are fictional)
- [ ] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| | | | | |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-11-drift-compare`, ready for review.
