# Validation — Phase 03: Eval harness

Roadmap: Stage 1 — Foundation, phase 03. Branch (created when work starts): `feat/phase-03-eval-harness`. Depends on: phase 02.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-03-eval-harness` can merge once every check below passes.

## 1. Quality gates

- [ ] `make check` passes (lint, format check, strict type check, tests)
- [ ] CI is green on the branch
- [ ] New code has unit tests; no test makes a network call

## 2. Behavior

- [ ] `load_set` parses `evals/default.yaml` and rejects a file with a missing field
- [ ] `run_eval` reports matched, false-block, and missed-block counts that agree with a hand-computed example
- [ ] `--tag` filters cases; `--no-model` never calls the model (asserted with a fake that fails if invoked)

## 3. Interfaces

- [ ] CLI: `langchaingov guard eval --guard <name> [--set] [--tag] [--json] [--no-model]`. Output modes and exit codes are covered by tests

## 4. Manual checks

- [ ] `guard eval --guard keyword-blocklist` with LiteLLM running completes on the default set and the summary looks plausible (log below)

## 5. Docs and specs

- [ ] The README covers `guard eval` and the YAML case format
- [ ] `specs/roadmap.md` marks phase 03 as done
- [ ] No real personal data is committed (all eval cases are fictional)
- [ ] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| | | | | |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-03-eval-harness`, ready for review.
