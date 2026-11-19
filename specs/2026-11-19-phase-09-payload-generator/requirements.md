# Requirements — Phase 09: Payload generator

Roadmap: Stage 3 — Golden set drift, phase 09. Branch (created when work starts): `feat/phase-09-payload-generator`. Depends on: phase 08.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

## Goal

`langchaingov golden build` generates the same context-filling needle-in-a-haystack payload, byte for byte, every time, at each rung of a fill ladder sized to a model's context window, and prints each payload's size, hash, and needle positions.

## Scope

### In scope

- **Model profiles**: `src/langchaingov/golden/models.yaml` maps a LiteLLM model name to `context_tokens` (the window the server actually serves, not the advertised maximum) and `local: true|false`. A model with no profile needs `--context N` and is treated as not local.
- **Golden set file**: `src/langchaingov/golden/data/default.yaml` with `name`, `description`, `generator_version`, `seed`, `fill_levels` (default `[0.25, 0.5, 0.75, 0.9]`), `output_reserve_tokens`, a fixed `system` prompt and answer instruction, and a list of fictional `needles` (`id`, `fact`, `question`, `answer`, `depth` from 0 to 1).
- **Schema and loader** in `golden/models.py` and `golden/loader.py` (pydantic, same style as `evals/`). Validation: unique needle ids, depth within 0..1, `answer` appears in `fact`, fill levels within (0, 1] and ascending.
- **Token counting** in `golden/tokens.py`: a `TokenCounter` protocol (`name`, `count(text) -> int`), a `TiktokenCounter` (`o200k_base`, imported lazily), and a `CharCounter` (characters / 4) used by tests and as a fallback.
- **Generator** in `golden/generator.py`: a pure function `(set, profile, level, counter) -> Payload`. A seeded `random.Random` builds fictional filler paragraphs from bundled sentence templates. The whole user message targets `floor(level × (context_tokens − output_reserve_tokens − system_tokens))`. The needles and question block are measured first, and filler paragraphs fill the rest, added until the next one would overshoot. The assembled prompt is then recounted and trimmed if the paragraph joins pushed it more than 1% over. Needles are placed between paragraphs nearest their depth, inside `<document>…</document>`, and the instruction and questions go last. Lower levels reuse a prefix of higher levels' filler. `Payload` carries `case_id` (e.g. `L050`), `level`, `target_tokens`, `est_tokens`, `chars`, `sha256`, `needle_depths` (where each needle actually landed), `paragraphs`, and `prompt` (left out of JSON).
- **CLI**: `langchaingov golden build [--set PATH] [--model M] [--context N] [--level F ...] [--dump DIR] [--json]`. It prints a table (level, target, estimated tokens, chars, short SHA-256, needle depths), and `--dump` writes each prompt to a `.txt` file for inspection. Exit 1 for an unknown model without `--context` or an invalid set file.
- `tiktoken` added to core dependencies.
- **Tests** (no network, `CharCounter` only): determinism (same inputs give the same SHA-256), a different seed gives a different hash, the size stays within tolerance of the target, needles appear in order near their depths, size grows with each level, loader errors, and CLI text, JSON, and exit codes.

### Out of scope

- Sending payloads to a model, scoring recall, and run files (phase 10).
- Run history, baselines, and drift comparison (phase 11).
- Model-specific token counts through LiteLLM's endpoint, and summarize-style cases ("Later / optional").

## Open questions

Check in with the user on each of these before implementing; if the answers change the phase plan, update `specs/roadmap.md` too.

- How many needles, and at which depths? (Proposal: 5 needles at 5/25/50/75/95%.) **Resolved:** 5 needles at depths 5/25/50/75/95%.
- Filler source: seeded sentence templates over a bundled fictional word list, or a bundled fictional text reshuffled by seed? (Proposal: templates; small, readable, no licensing questions.) **Resolved:** seeded sentence templates over bundled fictional word lists.
- Output reserve and size tolerance? (Proposal: 1,024 reserved output tokens; generated size within ±1% of target or one paragraph, whichever is larger.) **Resolved:** 1,024 reserved output tokens; size within ±1% of target or one paragraph, whichever is larger.
- Which models get a committed profile, and what context does the local Llama actually serve? (Ollama's default `num_ctx` is far below the model's advertised window unless it is raised, so the profile must match what the server is configured for. Phase 08 serves `llama3.2-3b-32k` at 32,768 tokens, local, so that is the first profile.) **Resolved:** only `llama3.2-3b-32k` (32,768 tokens, local). Other models need `--context`; cloud profiles are added later with verified window sizes.
- Should the ladder go to 100%? (Proposal: no, stop at 90%. tiktoken is only approximate for Llama, so 100% risks overflowing the real window.) **Resolved:** no; the ladder is 25/50/75/90%.

(When the phase starts, append ` **Resolved:** <answer>.` to each question.)

## Context

- `tech-stack.md` → "Golden-set drift": generation is pure and deterministic; any byte-changing generator change bumps `generator_version`.
- `tech-stack.md` → Token counting: tiktoken behind a protocol; tests inject the fake counter because tiktoken downloads its encoding on first use.
- `mission.md` principle 4: tests never touch the network.
- `mission.md` principle 6: the generator should read as an explanation of how a needle-in-a-haystack payload is built.
- Feature request part 1: "A consistent max generation of characters for tokens input maxing for context windows."
