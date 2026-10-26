# LangChain-native middleware: notes

Phase 05 wrapped LangChain 1.x agent middleware behind the same `Guardrail` protocol as the custom validators. What was learned, as of langchain 1.4.7.

## How the adapter works

`AgentMiddleware` exposes `before_model(state, runtime)` and `after_model(state, runtime)` hooks that `create_agent` calls around every model call. `MiddlewareGuard` calls those hooks directly on a one-message synthetic state (`{"messages": [HumanMessage(prompt)]}` for input, `[HumanMessage, AIMessage(reply)]` for output) with a default `Runtime()`. The middleware's own code decides; no agent loop or model call happens inside the guard, so the chain's single model call stays where it was.

Mapping of hook outcomes to verdicts:

| Hook result | Verdict |
| --- | --- |
| `None` | allow |
| `{"messages": [...]}` with a rewritten last message | modify (text threads to the next guard and the model) |
| `{"jump_to": "end", "messages": [AIMessage(note)]}` | block, reason = the note |
| raises a listed exception (`PIIDetectionError`) | block, reason = the exception |

## The three guards

- **`lc-pii`**: one `PIIMiddleware` per type. Built-in detectors: `email`, `credit_card`, `url` (also available: `ip`, `mac_address`). Phone and SSN are not built in; they reuse the regexes from the custom `pii-regex` guard via the `detector=` hook. Redaction tokens are the middleware's own (`[REDACTED_EMAIL]`), not ours. `strategy="block"` raises `PIIDetectionError`; `mask` and `hash` also exist.
- **`lc-custom-hooks`**: a `@before_model(can_jump_to=["end"])` function that returns `{"jump_to": "end"}` when the prompt contains a phrase, and an `@after_model` function that rewrites a word in the reply. This is all the plumbing a custom middleware needs.
- **`lc-hitl`**: LangChain's `HumanInTheLoopMiddleware` approves *tool calls* (`interrupt_on={"tool_name": True}`), so with a chat that has no tools it never fires. The guard instead uses the primitive it is built on: a two-node LangGraph graph whose node calls `interrupt(payload)`; the run returns with `__interrupt__`, the policy answers, and `invoke(Command(resume=answer), config)` finishes it. A `MemorySaver` checkpointer and a per-call `thread_id` are required for interrupts to work. `guard run` answers in the terminal; `guard eval` and tests have no policy, so an unanswered interrupt is a block.

## Compared with the custom validators

- The middleware brings ready-made detectors and strategies, but the message-list state model means every guard reasons about `HumanMessage`/`AIMessage` objects rather than plain text.
- Custom hooks are about as much code as a custom guard; the win is that the same function also plugs straight into `create_agent(middleware=[...])` for a real agent.
- Human-in-the-loop is the one capability the custom validators do not have, and it depends on LangGraph persistence (checkpointer + thread id), which the rest of the sandbox does not otherwise need.

## Open: real-model spike

No local model was configured in LiteLLM when this phase was built, so the planned spike (does `create_agent` with these middleware complete a turn against the real model?) is still a manual check in `validation.md`.
