# Requirements — Phase 05: LangChain-native middleware

Roadmap: Stage 2 — Guardrail families, phase 05. Branch (created when work starts): `feat/phase-05-langchain-middleware`. Depends on: phase 04.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

## Goal

Use LangChain 1.x's built-in agent middleware (PII detection, human-in-the-loop, custom before/after-model hooks) as guardrails, so the native approach can be compared with the hand-rolled one on the same eval set.

## Scope

### In scope

- `langchaingov.guards.middleware`: an adapter that runs a `create_agent` instance configured with LangChain middleware and maps its outcome to `Verdict`s.
- `lc-pii`: LangChain's PII middleware (email, phone, and so on) in redact mode on input and output.
- `lc-hitl`: human-in-the-loop middleware; in the CLI, an interrupt prompts `allow / block [a/b]`; in eval and tests, a policy callback decides automatically.
- `lc-custom-hooks`: a `@before_model` hook that blocks a listed phrase and an `@after_model` hook that rewrites a listed phrase, to show the hook mechanics.
- Tests with a fake chat model that supports the agent loop; interrupt handling tested with an injected policy.
- A short `docs/middleware-notes.md` recording what the middleware can and cannot do compared with the custom guards.

### Out of scope

- Tools for the agent beyond what the middleware needs.
- Persistent checkpointing for human-in-the-loop across processes.

## Open questions

Check in with the user on each of these before implementing; if the answers change the phase plan, update `specs/roadmap.md` too.

- Does the local Llama behind LiteLLM support tool calling well enough for `create_agent`? If not, should this phase use a plain chain with the middleware's underlying functions instead?
- Which built-in middleware to cover: PII and human-in-the-loop (recommended) only, or also summarization and model-fallback for completeness?
- How should human-in-the-loop behave in `guard eval`: auto-allow, auto-block, or skip those cases?

(When the phase starts, append ` **Resolved:** <answer>.` to each question.)

## Context

- `tech-stack.md` → third-party machinery is wrapped behind the protocol and never leaks into the CLI.
- `mission.md` principle 2 (one interface, many guardrails).
