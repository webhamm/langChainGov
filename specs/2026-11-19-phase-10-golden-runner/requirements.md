# Requirements — Phase 10: Golden runner

Roadmap: Stage 3 — Golden set drift, phase 10. Branch (created when work starts): `feat/phase-10-golden-runner`. Depends on: phase 09.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

## Goal

`langchaingov golden run` sends every fill-level payload to the model with fixed parameters and writes a JSONL run file recording, for each case, the response, its needle recall, token usage, finish reason, and latency.

## Scope

### In scope

- **Fixed request parameters**: temperature 0, `max_tokens` = the set's output reserve, a long per-request timeout, and a `seed` when the model's profile says the provider accepts one. `make_chat_model` in `llm.py` gains optional `max_tokens`, `timeout`, and `seed` arguments, so `llm.py` stays the one place that knows LiteLLM. All parameters are recorded in the run header.
- **Message shape**: the set's fixed `system` prompt, plus one user message holding the payload. The answer instruction asks for one line per question: `<needle id>: <answer>`.
- **Scoring** in `golden/scoring.py`: normalize (casefold, strip punctuation, collapse whitespace), then a needle counts as recalled when its normalized answer appears in the normalized response. Each case gets per-needle booleans and a recall fraction. Pure functions, deterministic, no LLM judge.
- **Run store** in `golden/store.py`: `RunHeader` (run id, UTC start time, package version, set name, set-file SHA-256, `generator_version`, seed, model, profile, request params, counter name, base-URL host) and `CaseResult` (case id, level, repeat index, target and estimated tokens, prompt SHA-256 and chars, reported prompt and completion tokens, finish reason, latency ms, response text, per-needle recall, recall fraction, `suspected_truncation`, error). Written to `<runs_dir>/<run_id>.jsonl`: header first, each case appended and flushed as it finishes. `runs_dir` is a setting (`LANGCHAINGOV_RUNS_DIR`, default `runs/golden`), and `runs/` is git-ignored.
- **Runner** in `golden/runner.py`: builds payloads (phase 09), invokes the model, times the call, and reads `usage_metadata` and `response_metadata["finish_reason"]` from the reply. A context-length or other `BadRequestError` is recorded as that case's error and the run continues. Connection and auth errors abort with the existing `_client_errors` hints.
- **Truncation check**: flag `suspected_truncation` when the reported prompt tokens fall well below the estimate. This catches a server silently cutting the prompt to a small `num_ctx`.
- **Local-first guard**: a model whose profile is not `local` (or that has no profile) is refused unless `--allow-cloud` is given. With `--allow-cloud`, the run is refused up front if its estimated prompt tokens exceed the cloud token cap (setting plus `--max-prompt-tokens`).
- **CLI**: `langchaingov golden run [--set PATH] [--model M] [--context N] [--level F ...] [--repeat N] [--allow-cloud] [--max-prompt-tokens N] [--json]`. It shows a live table (level, estimated vs reported tokens, recall, finish reason, latency, truncation flag) and prints the run-file path. Exit 0 when all cases completed, 1 on a config or connection error, and 4 when the run finished but some cases errored (all codes covered by tests).
- **Tests**: a fake chat model (in `tests/fakes.py`) that returns canned answers with `usage_metadata` and `finish_reason`; scoring tables; store round-trip and partial-run append; cloud refusal and cap; truncation flag; per-case error recording; CLI output and exit codes.

### Out of scope

- Listing runs, baselines, and comparing runs (phase 11).
- Sending payloads through `GuardedChain`, and embedding similarity ("Later / optional").
- Concurrency: cases run one after another, so latency numbers are comparable.

## Open questions

Check in with the user on each of these before implementing; if the answers change the phase plan, update `specs/roadmap.md` too.

- Does `--repeat` belong in the MVP, and with what default? (Proposal: yes, default 1. Repeats separate in-run nondeterminism from drift over time.) **Resolved:** yes, `--repeat N`, default 1.
- Cloud cap: per payload or per run total, and what default? (Proposal: per run total of estimated prompt tokens, default 50,000, so a cloud run is a deliberate choice.) **Resolved:** per-run total of estimated prompt tokens across payloads × repeats; default 50,000 (`LANGCHAINGOV_GOLDEN_CLOUD_TOKEN_CAP`, overridable with `--max-prompt-tokens`); only applies to non-local models.
- Scoring strictness: answer anywhere in the response, or only on the line labeled with the needle id? (Proposal: anywhere for the MVP; the labeled-line check is a later refinement.) **Resolved:** anywhere in the response, on whole-word boundaries after normalizing.
- Seed: send it only when the profile has `supports_seed: true`, or always and let LiteLLM drop it? (Proposal: profile flag; record "requested" vs "sent".) **Resolved:** profile flag `supports_seed` (true for `llama3.2-3b-32k`; LiteLLM's `ollama_chat` route forwards `seed`). The header records requested and sent.
- Per-request timeout for long local prompts? (Proposal: 600 s, as a setting.) **Resolved:** 600 s (`LANGCHAINGOV_GOLDEN_TIMEOUT`), with no client retries, so a slow case can't silently triple. A timeout is recorded as that case's error.
- Run id format? (Proposal: `YYYYMMDDTHHMMSSZ-<model-slug>`, sortable and readable.) **Resolved:** `YYYYMMDDTHHMMSSZ-<model-slug>`.

(When the phase starts, append ` **Resolved:** <answer>.` to each question.)

## Context

- `tech-stack.md` → "Golden-set drift": the runner measures the raw model through `make_chat_model`, not `GuardedChain`; scoring is deterministic; prompts are stored only as hashes.
- `mission.md` principle 1: local first; cloud only behind `--allow-cloud` with a token cap.
- `mission.md` principle 4: tests use fakes; real runs are manual checks logged here.
- Calibration from phase 09 (2026-11-19, `llama3.2-3b-32k`): Llama's reported prompt tokens were 0.7–0.9% above tiktoken's estimate (system prompt and chat template included), so the 90% rung used 87% of the window. The 90% rung took about 2 minutes on an M3 Pro. Size the truncation threshold and the timeout from this.
- Feature request part 2: "A method of sending out the request that is consistent and captures the return result."
