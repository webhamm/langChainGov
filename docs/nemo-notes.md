# NeMo Guardrails: notes

Phase 07 wrapped NVIDIA NeMo Guardrails (`nemoguardrails` 0.24.1, Colang 2.x) behind the `Guardrail` protocol as an optional extra. What was learned.

## Install and model path

```sh
uv sync --extra nemo
```

NeMo 0.24 no longer depends on LangChain; its `openai` engine uses its own OpenAI-compatible client, so the rails talk to LiteLLM directly. The adapter renders the `models` entry of `rails/config.yml` from the sandbox settings (`LANGCHAINGOV_BASE_URL`, `LANGCHAINGOV_MODEL`, the key) at build time, so there is still one source of truth. For the self-check rails NeMo makes its own model calls, one per rail per message, plus one for intent generation.

On first use NeMo downloads a small sentence-embedding model (FastEmbed, `all-MiniLM-L6-v2`) that it uses to pick the most relevant user intents for the intent prompt. FastEmbed caches it in its own temp directory (`FASTEMBED_CACHE_PATH` pins the location). The unit tests force `HF_HUB_OFFLINE=1` and skip if the model is not cached.

## What the config does

`src/langchaingov/guards/nemo/rails/` holds one Colang file and one YAML file.

- **Self-check input / output** (`nemoguardrails.library.self_check.*`): an LLM prompt per message, answered Yes/No. The prompts in `config.yml` describe the houseplant-care policy. `enable_rails_exceptions: true` makes a block come back as an `InputRailException` / `OutputRailException` event instead of a canned bot message, which is what the adapter reads.
- **Topic rail as Colang flows**: `flow user asked about taxes: user said "..." or user said "..."` defines an intent by example; `@active flow handle off topic taxes: user asked about taxes; bot refuse off topic` links it to a canned refusal. `activate generating user intent for unhandled user utterance` (from NeMo's `llm` library) asks the model to map any paraphrase onto one of the defined intents, which is how "Could you sort out my tax return?" reaches the taxes flow.
- **No `llm continuation`**: the sandbox's `GuardedChain` calls the model, so the rails never generate an answer. Without it, a benign prompt returns an empty reply, which the adapter reads as allow.
- **Output check on an existing reply**: `flow check bot reply: global $bot_message; match CheckReply() as $e; $bot_message = $e.text; await run output rails $e.text`. The adapter sends a `CheckReply` event through `process_events`, so NeMo runs its output rails on text it did not generate. Setting `$bot_message` matters: the self-check output action reads the reply from that global, and with it unset it blocks without calling the model.

## Things that did not work as expected

- `activate llm continuation` makes `generate(messages=...)` return a `TimerBotAction` tool call with empty content: in Colang 2 the host is expected to drive timer events for the asynchronous LLM reply. The chat CLI does that; a one-shot `generate` does not. Dropping it was the fix, and it also removed a wasted model call.
- `GenerationOptions(rails=["input"])` does not restrict stages under Colang 2: the input, intent, and general prompts all ran. The custom-event approach above replaced it for the output stage.
- `activate tracking unhandled user intent state` logged a `ColangValueError` (`$flow.flow_name` missing) on every benign prompt; it is not needed and was left out.
- The output self-check action takes the bot message from the `$bot_message` global, not from the flow argument; a custom flow that forgets to set it gets a silent block.
- Topic flows match paraphrases only through the intent prompt, so a weak model (or no model) means only the exact example sentences are caught.

## Compared with the other families

- NeMo is the only family where the guardrail owns the conversation: rails, dialog flows, and generation are one state machine. Fitting that into a per-stage protocol took two tricks (no continuation, custom event) and the result still spends two or three model calls per turn before the sandbox's own call.
- Colang 2 flows are the most readable way to express "when the user asks X, refuse" seen in this sandbox, and the intent prompt generalises them without writing a classifier.
- The self-check prompts are the same idea as the custom `llm-judge`, with NeMo's prompt templates and Yes/No parsing instead of JSON.

## Open: real runs

No local chat model was configured in LiteLLM when this phase was built, so every result above comes from a fake model answering the self-check and intent prompts. `validation.md` keeps the real run as a manual check.
