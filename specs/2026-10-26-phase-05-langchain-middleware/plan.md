# Plan — Phase 05: LangChain-native middleware

Roadmap: Stage 2 — Guardrail families, phase 05. Branch (created when work starts): `feat/phase-05-langchain-middleware`. Depends on: phase 04.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

See `requirements.md` for scope and decisions, and `validation.md` for the merge bar.

## 1. Branch

1.1. Create `feat/phase-05-langchain-middleware` from `main`, with phase 04 merged.

## 2. Spike

2.1. Confirm against the running LiteLLM whether `create_agent` with the chosen model completes a no-tool turn and a middleware interrupt. Record the result in `docs/middleware-notes.md`. Decide the adapter shape from this.

## 3. Adapter and guards

3.1. `src/langchaingov/guards/middleware/adapter.py`: builds the agent with a given middleware list, invokes it, converts interrupts and modified messages to `Verdict`s.
3.2. `src/langchaingov/guards/middleware/pii.py`, `hitl.py`, `hooks.py`: the three guards. Register `lc-pii`, `lc-hitl`, `lc-custom-hooks`.
3.3. Tests in `tests/guards/middleware/` with a fake model and an injected HITL policy.

## 4. Docs

4.1. `docs/middleware-notes.md`: observations and the comparison with custom validators.

## 5. Wrap-up

5.1. Bump the version to `0.5.0` (pyproject and `__version__` must match).
5.2. Update the README with the three guards.
5.3. Mark phase 05 done in `specs/roadmap.md`.
5.4. Work through `validation.md` and record the results.
