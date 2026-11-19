# Plan — Phase 10: Golden runner

Roadmap: Stage 3 — Golden set drift, phase 10. Branch (created when work starts): `feat/phase-10-golden-runner`. Depends on: phase 09.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

See `requirements.md` for scope and decisions, and `validation.md` for the merge bar.

## 1. Branch

1.1. Create `feat/phase-10-golden-runner` from `main`, with phase 09 merged.

## 2. Model client and settings

2.1. `llm.make_chat_model`: add optional `max_tokens`, `timeout`, `seed` (via `model_kwargs`). Existing callers are unchanged. Tests in `tests/test_llm.py`.
2.2. `Settings`: `runs_dir`, `golden_timeout`, `golden_cloud_token_cap`. Tests in `tests/test_settings.py`.
2.3. Add `runs/` to `.gitignore`.
2.4. `ModelProfile` gains `supports_seed`.

## 3. Scoring and storage

3.1. `golden/scoring.py`: `normalize`, `score(response, needles) -> NeedleScores`. Table-driven tests in `tests/golden/test_scoring.py`.
3.2. `golden/store.py`: `RunHeader`, `CaseResult`, `RunWriter` (create, append+flush), `read_run(path)`. Tests in `tests/golden/test_store.py`, including reading a file cut off mid-run.

## 4. Runner

4.1. `tests/fakes.py`: `UsageFakeChatModel` returning canned replies with `usage_metadata` and `finish_reason`.
4.2. `golden/runner.py`: `plan_run` (payloads × repeats, cloud check, cap check) and `execute_run` (invoke, time, score, truncation flag, per-case error capture, write). Tests in `tests/golden/test_runner.py`.

## 5. CLI

5.1. `golden run` in `cli.py`, reusing `_configured_model` and `_client_errors`, with a rich live table and a `--json` summary. Tests in `tests/test_cli_golden.py`: success, cloud refusal, cap refusal, partial errors exit 4, connection error exit 1.

## 6. Wrap-up

6.1. Bump the version to 0.10.0.
6.2. Update the README: `golden run`, the run-file format, `--allow-cloud`, and the truncation warning.
6.3. Mark phase 10 done in `specs/roadmap.md`.
6.4. Work through `validation.md` and record the results.
