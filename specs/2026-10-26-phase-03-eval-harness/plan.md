# Plan — Phase 03: Eval harness

Roadmap: Stage 1 — Foundation, phase 03. Branch (created when work starts): `feat/phase-03-eval-harness`. Depends on: phase 02.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

See `requirements.md` for scope and decisions, and `validation.md` for the merge bar.

## 1. Branch

1.1. Create `feat/phase-03-eval-harness` from `main`, with phase 02 merged.

## 2. Case set and loader

2.1. `evals/default.yaml` with fictional cases across the agreed categories. Add `pyyaml` as a dependency.
2.2. `src/langchaingov/evals/models.py`: `EvalCase`, `EvalSet`. `src/langchaingov/evals/loader.py`: `load_set(path)`. Tests in `tests/evals/test_loader.py` including an invalid-file case.

## 3. Runner and report

3.1. `src/langchaingov/evals/runner.py`: `run_eval(eval_set, chain, no_model=False) -> EvalReport`. `EvalReport` has rows (`case_id`, `expected`, `actual`, `matched`, `reason`) and totals. Tests in `tests/evals/test_runner.py` with stub guards.

## 4. CLI

4.1. `guard eval` command with the flags from requirements; Rich table and `--json`. Tests in `tests/test_cli_eval.py`.

## 5. Wrap-up

5.1. Bump the version to `0.3.0` (pyproject and `__version__` must match).
5.2. Update the README for `guard eval` and the eval file format.
5.3. Mark phase 03 done in `specs/roadmap.md`.
5.4. Work through `validation.md` and record the results.
