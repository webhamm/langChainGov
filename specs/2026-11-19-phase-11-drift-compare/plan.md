# Plan — Phase 11: Drift compare

Roadmap: Stage 3 — Golden set drift, phase 11. Branch (created when work starts): `feat/phase-11-drift-compare`. Depends on: phase 10.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

See `requirements.md` for scope and decisions, and `validation.md` for the merge bar.

## 1. Branch

1.1. Create `feat/phase-11-drift-compare` from `main`, with phase 10 merged.

## 2. History and baselines

2.1. `golden/store.py`: `list_runs`, `RunSummary` (status, mean recall), `load_baselines` / `pin_baseline` over `baselines.json`. Tests in `tests/golden/test_store.py`.
2.2. Fixture run files in `tests/golden/data/` (baseline, stable rerun, drifted rerun, different-generator rerun, partial run).

## 3. Comparison

3.1. `Settings`: drift thresholds (`drift_min_similarity`, `drift_prompt_token_pct`).
3.2. `golden/compare.py`: `check_compatible`, `compare_runs -> DriftReport` (per-level rows, flags with metric, value, and threshold, overall verdict). Tests in `tests/golden/test_compare.py`, with each rule tested at and just past its threshold.

## 4. CLI

4.1. `golden runs`, `golden baseline`, and `golden compare` in `cli.py`; the verdict line is colored; exit codes 0/1/3. Tests in `tests/test_cli_golden.py`.

## 5. Wrap-up

5.1. Bump the version to 0.11.0.
5.2. Update the README with the MVP runbook (build → run → baseline → run → compare) and how to read the drift table.
5.3. Mark phase 11 done in `specs/roadmap.md`.
5.4. Work through `validation.md` and record the results, including the end-to-end MVP run.
