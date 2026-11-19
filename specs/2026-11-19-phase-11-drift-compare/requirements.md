# Requirements — Phase 11: Drift compare

Roadmap: Stage 3 — Golden set drift, phase 11. Branch (created when work starts): `feat/phase-11-drift-compare`. Depends on: phase 10.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

## Goal

`langchaingov golden compare` tells the user, per fill level, whether a run has drifted from the pinned baseline (needle recall, response text, length, latency, served token count) and exits non-zero when it has. This completes the Stage 3 MVP.

## Scope

### In scope

- **History**: `golden/store.py` gains `list_runs(runs_dir)`. `langchaingov golden runs [--model M] [--json]` prints run id, date, model, set, levels, mean recall, and status (complete / partial / errors).
- **Baselines**: `langchaingov golden baseline <run_id>` pins a run as the baseline for its (set, model) pair in `<runs_dir>/baselines.json`; `golden baseline --show` lists the pins. Only complete runs can be pinned.
- **Comparison** in `golden/compare.py`, a pure function `(baseline, current, thresholds) -> DriftReport`:
  - Compatibility first: same set-file SHA-256, same `generator_version`, and the same prompt SHA-256 per case. A mismatch is "not comparable" with the reason, never drift. A different model is refused unless `--cross-model` is given.
  - Cases are matched by `(case_id, repeat)`. Per level: baseline vs current recall and its delta, needles lost and gained, difflib `SequenceMatcher` similarity of the two responses, response length change %, latency change %, reported prompt-token change, and finish-reason change.
  - Drift rules with default thresholds (settings, overridable by flags): any needle lost, similarity below the threshold, or a finish-reason change is **drift**. A reported prompt-token change beyond the threshold is an **environment change** warning (the tokenizer or serving setup moved). Latency is informational only.
- **CLI**: `langchaingov golden compare [RUN_ID] [--baseline RUN_ID] [--cross-model] [--json]`. `RUN_ID` defaults to the latest run for the configured model, and the baseline to the pinned one. It prints a per-level table and a one-line verdict (`STABLE` / `DRIFT` / `NOT COMPARABLE`). Exit 0 stable, 3 drift, 1 not comparable or a missing run/baseline.
- **README runbook**: the end-to-end MVP loop (build, run, pin baseline, run again later, compare), plus how to read the table.
- **Tests**: hand-built run files in `tests/golden/data/`; compatibility refusals; each drift rule at and just past its threshold; the environment-change warning; listing and baseline pinning; CLI text, JSON, and exit codes.

### Out of scope

- Embedding similarity, trends over many runs, charts, and scheduled runs ("Later / optional").
- Comparing different golden sets against each other.

## Open questions

Check in with the user on each of these before implementing; if the answers change the phase plan, update `specs/roadmap.md` too.

- Default thresholds? (Proposal: drift on any needle lost; text similarity < 0.90; finish-reason change. Environment warning when reported prompt tokens move > 2%.)
- With no pinned baseline, refuse or fall back to the earliest complete run for the same set and model? (Proposal: fall back, and say so in the output.)
- Exit code for drift? (Proposal: 3. Exit 2 already means "blocked" for `guard run`.)
- Should a prompt-token change count as drift rather than a warning? (Proposal: warning, since it signals the environment changed, not the model's answers.)
- Is `--against previous` (compare with the run just before, not the baseline) worth adding in the MVP? (Proposal: no, leave it for later.)
- With `--repeat N` runs, compare per repeat or on the aggregate (mean recall, min similarity)? (Proposal: aggregate per level, with per-repeat details in `--json`.)

(When the phase starts, append ` **Resolved:** <answer>.` to each question.)

## Context

- `tech-stack.md` → "Golden-set drift": compare refuses to compare across `generator_version`s; prompts are matched by SHA-256.
- `mission.md` "What success looks like": `golden run` followed later by `golden compare` shows drift per fill level and exits non-zero when it has.
- `mission.md` principle 3, applied here: every drift flag says which metric moved, by how much, and against which threshold.
- First real runs (phase 10, 2026-11-19, `llama3.2-3b-32k`, temperature 0, seed sent): 100% recall at every level, with identically formatted replies. Reported prompt tokens were 0.7–0.9% above the estimate. Latency was 26–100 s across the ladder, so latency changes are noisy and should stay informational. When a profile overstated the window, Ollama silently kept only half of `num_ctx`.
- Feature request part 3: "Evaluation for historical comparisons over time to determine differences and any drift in return potentially."
