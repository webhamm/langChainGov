# Plan — Phase 07: NeMo Guardrails

Roadmap: Stage 2 — Guardrail families, phase 07. Branch (created when work starts): `feat/phase-07-nemo-guardrails`. Depends on: phase 06.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

See `requirements.md` for scope and decisions, and `validation.md` for the merge bar.

## 1. Branch

1.1. Create `feat/phase-07-nemo-guardrails` from `main`, with phase 06 merged.

## 2. Install and spike

2.1. Add the `nemo` optional group; `uv sync --extra nemo`. Write a minimal `rails/config.yml` pointed at LiteLLM and confirm a plain generate works. Record findings in `docs/nemo-notes.md`.

## 3. Rails and adapter

3.1. `rails/` Colang files for the agreed rails; config renders base URL, model, and key from settings at build time.
3.2. `src/langchaingov/guards/nemo/adapter.py`: `NemoRailsGuard` building `LLMRails`, mapping outcomes to `Verdict`. Register `nemo-rails`.
3.3. Tests in `tests/guards/nemo/` with a stubbed rails object; config-load test skipped without the extra.

## 4. Docs

4.1. `docs/nemo-notes.md` and README section, including a short comparison across all four families.

## 5. Wrap-up

5.1. Bump the version to `0.7.0` (pyproject and `__version__` must match).
5.2. Update the README with the extra and the guard.
5.3. Mark phase 07 done in `specs/roadmap.md`.
5.4. Work through `validation.md` and record the results.
