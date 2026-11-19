# Plan — Phase 09: Payload generator

Roadmap: Stage 3 — Golden set drift, phase 09. Branch (created when work starts): `feat/phase-09-payload-generator`. Depends on: phase 08.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

See `requirements.md` for scope and decisions, and `validation.md` for the merge bar.

## 1. Branch

1.1. Create `feat/phase-09-payload-generator` from `main`, with phase 08 merged.

## 2. Golden set data and schema

2.1. `uv add tiktoken`.
2.2. `src/langchaingov/golden/__init__.py`, `models.py` (`Needle`, `GoldenSet`, `ModelProfile`, `Payload`) with validators. Tests in `tests/golden/test_models.py`.
2.3. `golden/loader.py`: load a set by path (default: the bundled `default.yaml`) and look up a model profile from `golden/models.yaml`, with `--context` as an override. A `GoldenSetError` gives one-line messages. Tests in `tests/golden/test_loader.py`.
2.4. Write `golden/data/default.yaml` (fictional needles only) and `golden/models.yaml`.

## 3. Token counting and generation

3.1. `golden/tokens.py`: `TokenCounter` protocol, `TiktokenCounter` (lazy import, cached encoder), `CharCounter`. Tests in `tests/golden/test_tokens.py` (CharCounter only).
3.2. `golden/generator.py`: seeded filler, sizing loop, needle placement, question block, SHA-256. Comments explain each step (principle 6). Tests in `tests/golden/test_generator.py`: determinism, seed sensitivity, size tolerance, needle order and depth, level monotonicity.

## 4. CLI

4.1. `golden` Typer sub-app in `cli.py` with `build`. A module-level `token_counter_factory` hook, like `model_factory`, so tests inject `CharCounter`. Tests in `tests/test_cli_golden.py`: table, `--json`, `--dump`, unknown model exit 1, bad set exit 1.

## 5. Wrap-up

5.1. Bump the version to 0.9.0 (`pyproject.toml` and `langchaingov.__version__`).
5.2. Update the README: what the golden set is and `golden build` usage.
5.3. Mark phase 09 done in `specs/roadmap.md`.
5.4. Work through `validation.md` and record the results.
