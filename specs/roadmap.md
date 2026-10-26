# Roadmap

Everything is a `Guardrail` behind one protocol, applied by one `GuardedChain`, exposed by one CLI, measured by one eval set. Phases are small and end to end: each ships a working command or a working guardrail family. Finish one before the next; check in before reordering.

Each phase's details are in `specs/<date>-phase-NN-<name>/`.

## Stage 1 — Foundation

1. ✅ **Scaffold and chat.** uv project, settings, `langchaingov chat` talking to LiteLLM, tests, `make check`, CI.
2. **Guardrail core.** `Guardrail` protocol, `Verdict`, `GuardedChain`, registry, and a first keyword-blocklist guard behind `guard list` and `guard run`.
3. **Eval harness.** A fictional YAML test set and `guard eval` that prints a verdict table and summary for any registered guardrail.

## Stage 2 — Guardrail families

4. **Custom validators.** Regex PII detection with redaction, a topic allowlist, and an LLM-as-judge guard that uses the local model.
5. **LangChain-native middleware.** LangChain agent middleware (PII, human-in-the-loop, custom before/after-model hooks) adapted to the protocol.
6. **Guardrails AI.** The `guardrails-ai` package and selected hub validators wrapped as guardrails, installed as an optional extra.
7. **NeMo Guardrails.** `nemoguardrails` with a Colang config for input and output rails, pointed at LiteLLM, wrapped as a guardrail.

## Later / optional

- Comparison report: `guard eval --all` running every family on the same set and printing one side-by-side table.
- Streamlit chat UI that shows which guardrail fired and why.
- FastAPI `/chat` endpoint with guardrails as middleware.
- LangSmith or OpenTelemetry tracing of guardrail verdicts.
- Public prompt-injection and jailbreak benchmark sets as extra eval files.
- Direct `langchain-ollama` backend as an alternative to LiteLLM.
