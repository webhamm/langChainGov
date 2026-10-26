# Requirements — Phase 04: Custom validators

Roadmap: Stage 2 — Guardrail families, phase 04. Branch (created when work starts): `feat/phase-04-custom-validators`. Depends on: phase 03.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

## Goal

Run three hand-rolled guardrails (regex PII, topic allowlist, LLM-as-judge) through `guard run` and `guard eval`, showing what can be done with no extra libraries.

## Scope

### In scope

- `pii-regex`: detects emails, phone numbers, and US SSN-shaped strings with regexes. Mode `redact` (default) replaces matches with `[EMAIL]` etc. and returns `modify`; mode `block` returns `block`. Applies to input and output.
- `topic-allowlist`: a configurable list of allowed topics plus a lightweight keyword check; anything clearly outside is blocked. Documented as a deliberately naive baseline for the LLM judge to beat.
- `llm-judge`: asks the same local model (via the shared `ChatOpenAI`) to classify the text against a rubric and return structured output (`safe: bool`, `category`, `reason`). Uses `with_structured_output` or a strict JSON prompt with a parser, whichever the local model handles reliably. Blocks when unsafe.
- All three registered; `guard list` shows them; `guard eval` runs on them.
- Tests: regex cases (positives, negatives, redaction text), allowlist cases, judge with a fake model returning canned JSON, judge handling of malformed model output (fail closed).

### Out of scope

- NER-based PII detection (Guardrails AI phase 06 covers a library approach).
- Multi-turn judge context.

## Open questions

Check in with the user on each of these before implementing; if the answers change the phase plan, update `specs/roadmap.md` too.

- Should `pii-regex` default to redacting (recommended) or blocking? **Resolved:** redact; `LANGCHAINGOV_PII_MODE=block` switches to blocking.
- Should the judge use the same model as chat (recommended for a one-model setup) or a separately configured `LANGCHAINGOV_JUDGE_MODEL`? **Resolved:** separate `LANGCHAINGOV_JUDGE_MODEL`; when unset the judge reuses the shared chat model.
- Judge rubric for v1: a short fixed list (prompt injection, harmful instructions, PII request, off-topic) or user-editable via a settings file? **Resolved:** `LANGCHAINGOV_JUDGE_RUBRIC` points at a plain-text rubric file; the built-in list (prompt injection, harmful/abusive, PII, off-topic for a houseplant-care assistant) is the default and the example format.

(When the phase starts, append ` **Resolved:** <answer>.` to each question.)

## Context

- `tech-stack.md` → guards that need the model receive the shared `ChatOpenAI` instance from the registry factory.
- `mission.md` principle 6 (learning over polish): these guards exist to show the mechanics plainly.
