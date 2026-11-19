# Roadmap

Everything is a `Guardrail` behind one protocol, applied by one `GuardedChain`, exposed by one CLI, measured by one eval set. Phases are small and end to end: each ships a working command or a working guardrail family. Finish one before the next; check in before reordering.

Each phase's details are in `specs/<date>-phase-NN-<name>/`.

## Stage 1 — Foundation

1. ✅ **Scaffold and chat.** uv project, settings, `langchaingov chat` talking to LiteLLM, tests, `make check`, CI.
2. ✅ **Guardrail core.** `Guardrail` protocol, `Verdict`, `GuardedChain`, registry, and a first keyword-blocklist guard behind `guard list` and `guard run`.
3. ✅ **Eval harness.** A fictional YAML test set and `guard eval` that prints a verdict table and summary for any registered guardrail.

## Stage 2 — Guardrail families

4. ✅ **Custom validators.** Regex PII detection with redaction, a topic allowlist, and an LLM-as-judge guard that uses the local model.
5. ✅ **LangChain-native middleware.** LangChain agent middleware (PII, human-in-the-loop, custom before/after-model hooks) adapted to the protocol.
6. ✅ **Guardrails AI.** The `guardrails-ai` package and selected hub validators wrapped as guardrails, installed as an optional extra.
7. ✅ **NeMo Guardrails.** `nemoguardrails` with a Colang config for input and output rails, pointed at LiteLLM, wrapped as a guardrail.

## Stage 3 — Golden set drift

From the feature request in `specs/goldenset-general-eval.md`. Phase 8 is the prerequisite local model; phases 9 to 11 are the MVP: after phase 11, `golden run` twice and `golden compare` reports drift end to end.

8. ✅ **Local model stack.** `make llm-up` stands up `llama3.2:3b` with a 32k window (versioned Ollama Modelfile) behind a repo-owned LiteLLM proxy run with `uvx`, plus `llm-down`, `llm-status`, and `llm-smoke`.
9. ✅ **Payload generator.** Model profiles, a seeded needle-in-a-haystack golden set, and `golden build`, which generates context-filling payloads at a 25/50/75/90% fill ladder sized with tiktoken.
10. ✅ **Golden runner.** `golden run` sends each payload with fixed parameters, scores needle recall, and appends every response with usage, latency, and hashes to a JSONL run file; local-first with `--allow-cloud` and a token cap.
11. ✅ **Drift compare.** `golden runs`, `golden baseline`, and `golden compare`, which diff a run against a pinned baseline per fill level (recall, text similarity, length, latency) and exit non-zero on drift.

## Later / optional

- Comparison report: `guard eval --all` running every family on the same set and printing one side-by-side table.
- Streamlit chat UI that shows which guardrail fired and why.
- FastAPI `/chat` endpoint with guardrails as middleware.
- LangSmith or OpenTelemetry tracing of guardrail verdicts.
- Public prompt-injection and jailbreak benchmark sets as extra eval files.
- Direct `langchain-ollama` backend as an alternative to LiteLLM.
- Second local model profile (e.g. `llama3.1:8b`) and Ollama KV-cache tuning for larger served windows.
- Golden set: semantic similarity with `text-embedding-3-small` through LiteLLM, next to difflib.
- Golden set: summarize-style cases on a fixed fictional corpus (drift without a known answer).
- Golden set: model-specific token counts through LiteLLM's token-counter endpoint.
- Golden set: `golden trend` across many runs (SQLite or a small chart), and scheduled runs.
- Golden set: `golden compare --against previous` (compare with the run just before, not the baseline).
- Golden set: run payloads through `GuardedChain --guard ...` to see whether guards change under long context.
