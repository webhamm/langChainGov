# Requirements — Phase 03: Eval harness

Roadmap: Stage 1 — Foundation, phase 03. Branch (created when work starts): `feat/phase-03-eval-harness`. Depends on: phase 02.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

## Goal

Run `langchaingov guard eval --guard <name>` against a fixed set of prompts and see, per case, whether the guardrail's verdict matched the expected one, plus a summary, so every later family can be measured the same way.

## Scope

### In scope

- `src/langchaingov/evals/data/default.yaml` (packaged so `guard eval` works from any directory; `--set` points at any other file): a fictional case set. Each case: `id`, `prompt`, `expected` (`allow|block`), `tags` (e.g. `benign`, `jailbreak`, `pii`, `off-topic`, `toxic`). Around 20 to 30 cases to start; all content invented, no real people.
- `langchaingov.evals`: loader (pydantic models for the file), runner that feeds each case through `GuardedChain` with the chosen guard(s), and a `EvalReport` with per-case rows and totals (matched, false blocks, missed blocks).
- CLI: `guard eval --guard <name> [--set file.yaml] [--tag <tag>] [--json] [--with-model]`. Without `--with-model` only input checks run, so a run is fast and offline. Rich table in text mode. Exit code 0 always unless the file is invalid.
- Tests: loader validation, runner with stub guards and fake model, report totals, CLI output.

### Out of scope

- Running every guard at once and comparing (Later / optional: comparison report).
- Metrics beyond counts (precision/recall can come with the comparison report).
- Public benchmark sets.

## Open questions

Check in with the user on each of these before implementing; if the answers change the phase plan, update `specs/roadmap.md` too.

- Which categories should the first case set cover? Proposed: benign, jailbreak/prompt-injection, PII in prompt, off-topic, toxic. Any to add or drop? **Resolved:** all five, as tags `benign`, `jailbreak`, `pii`, `off-topic`, `toxic`. The fictional assistant persona is a houseplant-care helper, so benign and off-topic have a concrete meaning.
- Should an eval run call the model by default (slower, exercises output checks) or default to `--no-model` and opt in to model calls? **Resolved:** input checks only by default; `--with-model` runs the full chain including output checks.
- Is a simple matched/false-block/missed-block count enough for now, or do you want precision and recall from the start? **Resolved:** counts only (matched, false blocks, missed blocks), overall and per tag. Expected `block` counts as matched when the guard blocks or modifies; expected `allow` only when nothing fires.

(When the phase starts, append ` **Resolved:** <answer>.` to each question.)

## Context

- `tech-stack.md` → the eval harness feeds cases through the same `GuardedChain` path as `guard run`.
- `mission.md` principle 2 (one interface, many guardrails) and the success criterion of a comparable table per family.
