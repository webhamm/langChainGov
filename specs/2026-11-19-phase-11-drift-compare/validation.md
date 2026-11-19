# Validation — Phase 11: Drift compare

Roadmap: Stage 3 — Golden set drift, phase 11. Branch (created when work starts): `feat/phase-11-drift-compare`. Depends on: phase 10.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

`feat/phase-11-drift-compare` can merge once every check below passes.

## 1. Quality gates

- [ ] `make check` passes (lint, format check, strict type check, tests). Lint, format, and mypy pass, and so do 296 tests. The same two NeMo tests that fail on `main` still fail (FastEmbed can't load `all-MiniLM-L6-v2` offline).
- [ ] CI is green on the branch (GitHub Actions billing is still blocked)
- [x] New code has unit tests; no test touches the network (comparison works on fixture run files)

## 2. Behavior

- [x] Runs with a different set hash, `generator_version`, or prompt hash are reported "not comparable" with the reason, never as drift (tested)
- [x] A different model is refused without `--cross-model` (tested)
- [x] Each drift rule fires just past its threshold and not at it, and the flag names the metric, value, and threshold (tested)
- [x] A prompt-token change is reported as an environment warning, not drift (tested)
- [x] `golden runs` shows complete, partial, and errored runs correctly; only complete runs can be pinned (tested)

## 3. Interfaces

- [x] CLI: `golden runs`, `golden baseline`, `golden compare`. Text and `--json` output, and exit codes 0/1/3, are covered by tests

## 4. Manual checks

- [x] End-to-end MVP on the local Llama: `golden run`, `golden baseline <id>`, `golden run` again, `golden compare` reports STABLE (or explains the drift it found) (logged below)
- [x] Induced drift: change the serving setup under the same model name and confirm `golden compare` reports DRIFT and exits 3 (logged below). Temperature 1 and 2 did not change this model's answers (see the run log), so drift was induced by silently serving the tag with `num_ctx 16384`.

## 5. Docs and specs

- [x] The README has the MVP runbook and explains the drift table
- [x] `specs/roadmap.md` marks phase 11 as done
- [x] No real personal data is committed (fixture runs are fictional)
- [x] Every open question in `requirements.md` is resolved and recorded

## Run log

| Date | Version | Inputs | Result | Reviewer notes |
| --- | --- | --- | --- | --- |
| 2026-11-19 | 0.11.0 | Phase 10 baseline `20261119T214340Z` pinned; fresh full-ladder `golden run`; `golden compare --model llama3.2-3b-32k` | STABLE, exit 0: similarity 1.000, prompt tokens +0.0%, recall 100% at all four levels | Run by Claude in the session. Latency −9% to −21% between runs: noise |
| 2026-11-19 | 0.11.0 | `LANGCHAINGOV_TEMPERATURE=1`, levels 25/90; then `=2`, level 25; compare | STABLE both times: byte-identical replies | Seeded sampling plus five easy facts. `chat` without a seed confirmed temperature reaches Ollama (T=2 varies, T=0 doesn't). L090 latency −98%: Ollama's prompt cache reused the identical prompt, so latency stays informational |
| 2026-11-19 | 0.11.0 | Same tag silently rebuilt with `num_ctx 16384`, `golden run -l 0.9`, compare | DRIFT, exit 3: recall 100% → 40% (vault-door, ferry-captain, logbook-page lost), similarity 0.551, plus environment warnings for prompt tokens −71.2% and truncation | Tag restored from `infra/ollama/…Modelfile`; `make llm-smoke` passed (context 32768) |
| 2026-11-19 | 0.11.0 | Overstated-context run (`--context 65536`) vs baseline | NOT COMPARABLE, exit 1: "L090 prompt differs …; context 32768 vs 65536 tokens" | |

## Definition of done

Every box is checked, and the phase's work is on `feat/phase-11-drift-compare`, ready for review.
