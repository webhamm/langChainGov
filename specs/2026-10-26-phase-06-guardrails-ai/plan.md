# Plan — Phase 06: Guardrails AI

Roadmap: Stage 2 — Guardrail families, phase 06. Branch (created when work starts): `feat/phase-06-guardrails-ai`. Depends on: phase 05.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

See `requirements.md` for scope and decisions, and `validation.md` for the merge bar.

## 1. Branch

1.1. Create `feat/phase-06-guardrails-ai` from `main`, with phase 05 merged.

## 2. Install and spike

2.1. Add the `guardrails-ai` optional group; `uv sync --extra guardrails-ai`; `guardrails configure`; install the chosen hub validators. Record versions and gotchas in `docs/guardrails-ai-notes.md`.

## 3. Adapter and guards

3.1. `src/langchaingov/guards/guardrails_ai/adapter.py`: `GuardrailsAiGuard(guard: Guard, name)` mapping outcomes to `Verdict`. Lazy import with a clear "install the extra" error.
3.2. One module per validator, registered as `gr-pii`, `gr-toxic`, `gr-topic` (names final when validators are chosen).
3.3. Tests in `tests/guards/guardrails_ai/` with a stub `Guard`; mark real-library tests to skip when the extra is absent.

## 4. Docs

4.1. `docs/guardrails-ai-notes.md` and README section.

## 5. Wrap-up

5.1. Bump the version to `0.6.0` (pyproject and `__version__` must match).
5.2. Update the README with the extra and the guards.
5.3. Mark phase 06 done in `specs/roadmap.md`.
5.4. Work through `validation.md` and record the results.
