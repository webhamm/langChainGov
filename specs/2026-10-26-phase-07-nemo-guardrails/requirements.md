# Requirements — Phase 07: NeMo Guardrails

Roadmap: Stage 2 — Guardrail families, phase 07. Branch (created when work starts): `feat/phase-07-nemo-guardrails`. Depends on: phase 06.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

## Goal

Run NVIDIA NeMo Guardrails with a Colang config (input and output rails) against the local model through LiteLLM, wrapped as a guardrail, and compare it with the other families on the eval set.

## Scope

### In scope

- Optional dependency group `nemo` in `pyproject.toml`; lazy import like phase 06.
- `rails/` directory with `config.yml` (engine `openai`, base URL and model from our settings) and Colang files defining: an input rail (self-check input / jailbreak), an output rail (self-check output), and a topic rail that refuses off-topic requests.
- `langchaingov.guards.nemo`: adapter that builds `LLMRails` from the config, runs `generate`, and maps refusals or rail stops to `block`, otherwise `allow` (and `modify` if the rails rewrite output).
- Registered as `nemo-rails`.
- Tests: adapter mapping with a stubbed rails object; config files validated by loading them (skipped when the extra is absent).
- `docs/nemo-notes.md` with setup, Colang version used, and comparison notes.

### Out of scope

- Dialog flows beyond simple refusals.
- NeMo's own fact-checking or retrieval rails.

## Open questions

Check in with the user on each of these before implementing; if the answers change the phase plan, update `specs/roadmap.md` too.

- Colang 1.0 (simpler, widely documented) or Colang 2.x for the rails?
- Which rails for v1: self-check input, self-check output, and a topic rail (recommended), or also the built-in jailbreak heuristics?
- NeMo must call the model itself for self-check rails. Is it acceptable that it bypasses our `ChatOpenAI` and talks to LiteLLM directly with the same settings?

(When the phase starts, append ` **Resolved:** <answer>.` to each question.)

## Context

- `tech-stack.md` → guardrail libraries are optional extras; the model endpoint is the local LiteLLM proxy.
- `mission.md` principle 1 (local first) and principle 2 (one interface, many guardrails).
