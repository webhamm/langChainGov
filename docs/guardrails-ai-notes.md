# Guardrails AI: notes

Phase 06 wrapped the `guardrails-ai` package (0.11.0) behind the `Guardrail` protocol as an optional extra. What was learned.

## Install

```sh
uv sync --extra guardrails-ai
```

The extra brings `guardrails-ai`, Presidio (analyzer + anonymizer), the small spaCy English model `en_core_web_sm` (as a wheel URL, no `spacy download` step), `transformers` and `torch`. Classifier weights download from the Hugging Face hub on first use of `gr-toxic` (`unitary/toxic-bert`) and `gr-topic` (`MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33`); they are cached under `~/.cache/huggingface`.

Side effect to know about: `guardrails-ai` depends on `litellm`, which caps `openai<3`. uv locks one version per package across all extras, so the whole project moved from openai 3.x to 2.x when the extra was added. Nothing in the sandbox needed 3.x, but it is a real cost of this dependency.

## Why the validators live in this repo

The hub validators `DetectPII`, `ToxicLanguage` and `RestrictToTopic` are installed with `guardrails hub install hub://guardrails/...`, which needs a Guardrails Hub token (`guardrails configure`). This sandbox has no hub account. Installing the validators straight from their GitHub repos does not work either: each repo ships a top-level package literally named `validator`, so two of them collide in one environment (the hub CLI avoids that by renaming them into `guardrails.hub.*`).

So `src/langchaingov/guards/guardrails_ai/validators.py` reimplements the three on the public `Validator` API with the same engines the hub versions use:

| Validator | Engine | Fail behaviour |
| --- | --- | --- |
| `langchaingov/detect_pii` | Presidio analyzer + anonymizer (`en_core_web_sm`) | `fix_value` = Presidio's anonymised text (`<EMAIL_ADDRESS>` ...) |
| `langchaingov/toxic_language` | transformers text classification, `unitary/toxic-bert`, all labels | fails when any label scores at or above the threshold |
| `langchaingov/restrict_to_topic` | transformers zero-shot classification | fails unless the top label is a valid topic at or above the threshold |

Each takes its engine as an optional constructor argument, which is how the unit tests stay offline.

## The adapter

`GuardrailsAiGuard` calls `Guard().use(validator).validate(text)` and maps the `ValidationOutcome`:

| Guardrails outcome | Verdict |
| --- | --- |
| `validation_passed` and `validated_output == text` | allow |
| `validation_passed` and a different `validated_output` (`OnFailAction.FIX`) | modify |
| `ValidationError` raised (`OnFailAction.EXCEPTION`) | block, reason = the validator's `error_message` |
| `validation_passed` false without an exception (`NOOP`, `FILTER`...) | block |

`gr-pii` uses `FIX` in redact mode and `EXCEPTION` in block mode; `gr-toxic` and `gr-topic` use `EXCEPTION`.

Presidio also applies validity rules: the textbook fake SSN `123-45-6789` is on its deny list and is never reported, so the packaged eval case uses `219-09-9999`, the sample number printed on the Social Security Administration's example card.

## Telemetry

With the default `~/.guardrailsrc` (`enable_metrics=true`) the package sends hub telemetry to a remote OpenTelemetry collector, and prints connection warnings when it cannot. Flipping the in-memory setting is not enough: every `Guard()` reloads the rc file, and both `Guard()` and every `validate()` set `_enabled` on the process-wide `HubTelemetry` singleton again. The tracer, however, is created once in the singleton's constructor and both span paths return early when it is `None`, so the adapter sets `HubTelemetry()._tracer = None` (plus `settings.disable_tracing = True`) at import and after each `Guard` is built. The file on disk is left alone; `guardrails configure --disable-metrics` makes it permanent.

## Compared with the other families

- The `Validator` / `Guard` / `OnFailAction` model is the most explicit about what happens on failure (fix, exception, filter, reask, refrain), which maps cleanly onto allow / modify / block.
- The framework is heavy for this use: the extra pulls in torch and transformers even for the Presidio-only guard, and the hub workflow assumes an account.
- Presidio's entity model (names, locations, dates, more) is far richer than the regexes in `pii-regex` or the fixed types in LangChain's `PIIMiddleware`, at the cost of a spaCy model and false positives. With `en_core_web_sm` the NER entities are noisy: on the packaged eval set it labelled `Summarise` and `Ignorez` as PERSON, `AI` and `Zorbia` as LOCATION and `winter` as DATE_TIME, which rewrote a benign prompt. The default `LANGCHAINGOV_GR_PII_ENTITIES` therefore lists only the structured identifiers; add `PERSON,LOCATION,...` to opt in, ideally with a larger spaCy model.

## Open: real runs

The classifier guards were not run against the real models in this phase (no local chat model in LiteLLM yet, and the weights were not downloaded). `validation.md` keeps those as manual checks.
