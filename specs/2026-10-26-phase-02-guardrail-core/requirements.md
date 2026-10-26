# Requirements — Phase 02: Guardrail core

Roadmap: Stage 1 — Foundation, phase 02. Branch (created when work starts): `feat/phase-02-guardrail-core`. Depends on: phase 01.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

## Goal

Run `langchaingov guard run --guard keyword-blocklist "<prompt>"` and see the prompt either answered or blocked with a reason, through the one protocol every later guardrail will implement.

## Scope

### In scope

- `langchaingov.guards.base`: `Verdict` (action `allow|block|modify`, `reason`, `text`, `guard`, `stage` input/output), `Guardrail` protocol (`name`, `check_input`, `check_output`), `GuardedResult` (final `text`, `blocked: bool`, `verdicts: list[Verdict]`).
- `langchaingov.guards.registry`: `register(name, factory)`, `get(name, settings, model)`, `names()`. Factories receive settings and the chat model so guards that need the LLM get the same instance.
- `langchaingov.chain.GuardedChain`: runs input checks in order, stops at first `block`, threads `modify` text forward, calls the model, runs output checks the same way. Returns `GuardedResult`.
- First guard, `keyword-blocklist`: blocks input or output containing any of a configurable list of words (default list of a few fictional banned terms; overridable via `LANGCHAINGOV_BLOCKLIST`).
- CLI: `guard list` (names and one-line descriptions), `guard run --guard <name> [--guard <name>...] "<prompt>"` with `--json`. Text mode prints the verdict chain and the reply or the block reason. Exit code 0 for allow/modify, 2 for block.
- Tests: `GuardedChain` with fake model and stub guards covering allow, block on input, block on output, modify threading; registry unknown-name error; CLI output and exit codes.

### Out of scope

- Any guard beyond the keyword blocklist (phases 04–07).
- Evaluation over a test set (phase 03).
- Async or streaming execution.

## Open questions

Check in with the user on each of these before implementing; if the answers change the phase plan, update `specs/roadmap.md` too.

- When a guard raises an exception, fail closed (treat as block, recommended for a safety tool) or fail open (log and continue)? **Resolved:** fail closed; the exception becomes a `block` verdict whose reason names the guard and the error.
- Should `guard run` accept several `--guard` flags and apply them in order (recommended), or exactly one? **Resolved:** several, applied in the order given, on input and again on output.
- Exit code for a blocked prompt: 2 (recommended, distinct from errors) or 0 with the block printed? **Resolved:** 2 for blocked; 1 stays for configuration and proxy errors.

(When the phase starts, append ` **Resolved:** <answer>.` to each question.)

## Context

- `tech-stack.md` → the core pattern: everything is a `Guardrail`; the CLI only talks to `GuardedChain` and the registry.
- `mission.md` principle 2 (one interface, many guardrails) and principle 3 (every verdict explains itself).
