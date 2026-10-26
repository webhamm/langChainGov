# Mission

## Purpose

langChainGov is a personal learning sandbox for building LangChain applications against a local model and trying out guardrail techniques on them. It answers one question hands-on: given the same local model and the same set of risky prompts, how do the different guardrail approaches (LangChain-native middleware, hand-rolled validators, Guardrails AI, NeMo Guardrails) behave, and what do they cost in setup and complexity?

## Who it is for

The repo owner, learning by doing. Code is read more often than it is run by anyone else, so clarity beats generality. Nothing here is deployed or multi-user.

## Principles

1. **Local first.** Every model call goes to the local LiteLLM proxy (which fronts the local Llama). No cloud API keys are required to run anything.
2. **One interface, many guardrails.** Every guardrail family plugs into the same `Guardrail` protocol so they can be swapped by name and compared on the same test set.
3. **Every verdict explains itself.** When a guardrail blocks or modifies something, the result says which guardrail fired and why.
4. **Tests never touch the network.** Unit tests use fake chat models. Real-model runs are manual checks, logged in the phase's run log.
5. **Small, end-to-end phases.** Each phase ships one usable command or guardrail and is done in a session. Finish one before starting the next.
6. **Learning over polish.** Prefer readable, well-commented code that shows how a technique works over abstractions that hide it.

## Scope (v1)

### In

- A `langchaingov` CLI: chat with the local model, run a named guardrail on a prompt, evaluate guardrails against a prompt test set.
- A guardrail framework: protocol, verdicts, registry, a chain wrapper that applies input and output checks.
- Four guardrail families, each in its own phase: custom validators (regex, PII, LLM-as-judge), LangChain-native middleware, Guardrails AI, NeMo Guardrails.
- A small, fictional evaluation set of prompts (jailbreaks, PII, off-topic, benign) with expected verdicts.

### Out

- Web UI, HTTP API, deployment, authentication, multi-user state.
- Cloud model providers.
- Fine-tuning or training classifiers.
- Production-grade latency or throughput work.

## What success looks like

- `langchaingov chat "..."` answers from the local model through LiteLLM.
- `langchaingov guard eval --guard <name>` runs for every guardrail family on the same test set and prints a comparable table of verdicts.
- The repo owner can explain, from experience, the trade-offs between the four approaches.
