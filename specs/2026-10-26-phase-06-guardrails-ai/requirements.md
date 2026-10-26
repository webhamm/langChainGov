# Requirements — Phase 06: Guardrails AI

Roadmap: Stage 2 — Guardrail families, phase 06. Branch (created when work starts): `feat/phase-06-guardrails-ai`. Depends on: phase 05.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

## Goal

Wrap the `guardrails-ai` package and a few of its hub validators as guardrails, installed as an optional extra, and measure them on the same eval set.

## Scope

### In scope

- Optional dependency group `guardrails-ai` in `pyproject.toml`; `uv sync --extra guardrails-ai`. The core package imports it lazily so `guard list` still works without it (such guards show as "not installed").
- `langchaingov.guards.guardrails_ai`: an adapter from a `guardrails.Guard` to the `Guardrail` protocol, mapping validation failures to `block` and fixes to `modify`.
- Two or three validators from the hub, chosen in the open questions (candidates: `DetectPII`, `ToxicLanguage`, `RestrictToTopic`, `RegexMatch`).
- Setup docs: `guardrails configure`, hub installs, any model downloads, all kept local.
- Tests: adapter mapping with a stubbed `Guard`; the real library exercised only in a manual check.

### Out of scope

- Guardrails AI's own LLM-calling features; the model stays behind our `ChatOpenAI`.
- Guardrails server mode.

## Open questions

Check in with the user on each of these before implementing; if the answers change the phase plan, update `specs/roadmap.md` too.

- Which hub validators to include? Proposed: `DetectPII` and `ToxicLanguage` (both run locally), plus `RestrictToTopic` if its model download is acceptable.
- Hub installs need a Guardrails Hub token; is creating a free account acceptable, or restrict to validators that ship without the hub?
- If `guardrails-ai` does not support the pinned Python, is a separate uv environment for this phase acceptable?

(When the phase starts, append ` **Resolved:** <answer>.` to each question.)

## Context

- `tech-stack.md` → guardrail libraries are optional extras; third-party machinery never leaks into the CLI.
- `mission.md` principle 1 (local first) and principle 2 (one interface, many guardrails).
