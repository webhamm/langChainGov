# Plan — Phase 04: Custom validators

Roadmap: Stage 2 — Guardrail families, phase 04. Branch (created when work starts): `feat/phase-04-custom-validators`. Depends on: phase 03.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

See `requirements.md` for scope and decisions, and `validation.md` for the merge bar.

## 1. Branch

1.1. Create `feat/phase-04-custom-validators` from `main`, with phase 03 merged.

## 2. Regex and allowlist guards

2.1. `src/langchaingov/guards/custom/pii_regex.py`: patterns, `PiiRegex(mode)`, redaction. Tests in `tests/guards/test_pii_regex.py`.
2.2. `src/langchaingov/guards/custom/topic_allowlist.py`: `TopicAllowlist(topics)`. Tests in `tests/guards/test_topic_allowlist.py`.

## 3. LLM judge

3.1. `src/langchaingov/guards/custom/llm_judge.py`: rubric prompt, `JudgeVerdict` pydantic model, `LlmJudge(model)`; fail closed on parse errors. Tests in `tests/guards/test_llm_judge.py` with `FakeListChatModel` returning JSON and garbage.

## 4. Registration and eval

4.1. Register `pii-regex`, `topic-allowlist`, `llm-judge`. Add PII and off-topic cases to `evals/default.yaml` if missing.

## 5. Wrap-up

5.1. Bump the version to `0.4.0` (pyproject and `__version__` must match).
5.2. Update the README with the three guards and their settings.
5.3. Mark phase 04 done in `specs/roadmap.md`.
5.4. Work through `validation.md` and record the results.
