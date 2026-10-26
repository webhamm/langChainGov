# Validation — Phase 03: Eval harness

Roadmap: Stage 1 — Foundation, phase 03. Branch (created when work starts): `feat/phase-03-eval-harness`. Depends on: phase 02.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-03-eval-harness` can merge once every check below passes.

## 1. Quality gates

- [x] `make check` passes (lint, format check, strict type check, tests)
- [ ] CI is green on the branch
- [x] New code has unit tests; no test makes a network call

## 2. Behavior

- [x] `load_set` parses the packaged `default.yaml` and rejects a file with a missing field
- [x] `run_eval` reports matched, false-block, and missed-block counts that agree with a hand-computed example
- [x] `--tag` filters cases; without `--with-model` the model is never called (asserted with a fake that fails if invoked)

## 3. Interfaces

- [x] CLI: `langchaingov guard eval --guard <name> [--set] [--tag] [--json] [--with-model]`. Output modes and exit codes are covered by tests

## 4. Manual checks

- [x] `guard eval --guard keyword-blocklist` completes on the default set (offline mode; `--with-model` waits on a local model) and the summary looks plausible (log below)

## 5. Docs and specs

- [x] The README covers `guard eval` and the YAML case format
- [x] `specs/roadmap.md` marks phase 03 as done
- [x] No real personal data is committed (all eval cases are fictional)
- [x] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| 2026-10-26 | 0.3.0 | `uv run langchaingov guard eval -g keyword-blocklist --json` (offline, packaged default set, 26 cases) | 6 matched (all benign), 0 false blocks, 20 missed blocks (all jailbreak/pii/off-topic/toxic). Expected: the default blocklist words do not occur in the set, so it is a clean baseline for phase 04. | `--with-model` run waits on a local model in LiteLLM; CI skipped by decision. |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-03-eval-harness`, ready for review.
