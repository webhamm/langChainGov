"""Three validators written on the Guardrails AI ``Validator`` API.

The hub versions (``DetectPII``, ``ToxicLanguage``, ``RestrictToTopic``) need a hub
account to install, so these are small local reimplementations on the same engines:
Presidio for PII, a transformers text classifier for toxicity, and a zero-shot
classifier for topic. The ML engines load lazily on first use and can be injected,
which is how the unit tests stay offline and fast.
"""

from collections.abc import Callable
from typing import Any

from guardrails.classes.validation.validation_result import (
    FailResult,
    PassResult,
    ValidationResult,
)
from guardrails.validator_base import Validator, register_validator

TOXIC_MODEL = "unitary/toxic-bert"
TOPIC_MODEL = "MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33"

TextScores = Callable[[str], dict[str, float]]
"""Classifier: text -> {label: score}."""
TopicScores = Callable[[str, list[str]], dict[str, float]]
"""Zero-shot classifier: (text, candidate labels) -> {label: score}."""


# --- engines (lazy, replaceable in tests) -------------------------------------------


def load_presidio() -> tuple[Any, Any]:
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine

    provider = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }
    )
    analyzer = AnalyzerEngine(nlp_engine=provider.create_engine(), supported_languages=["en"])
    return analyzer, AnonymizerEngine()  # type: ignore[no-untyped-call]


def load_text_classifier(model: str) -> TextScores:
    from transformers import pipeline

    classifier = pipeline("text-classification", model=model, top_k=None)

    def scores(text: str) -> dict[str, float]:
        raw = classifier(text, truncation=True)
        rows = raw[0] if raw and isinstance(raw[0], list) else raw
        return {row["label"]: float(row["score"]) for row in rows}

    return scores


def load_zero_shot(model: str) -> TopicScores:
    from transformers import pipeline

    classifier = pipeline("zero-shot-classification", model=model)

    def scores(text: str, labels: list[str]) -> dict[str, float]:
        raw = classifier(text, candidate_labels=labels, multi_label=False)
        return dict(zip(raw["labels"], (float(s) for s in raw["scores"]), strict=True))

    return scores


# --- validators ------------------------------------------------------------------------


@register_validator(name="langchaingov/detect_pii", data_type="string")
class DetectPii(Validator):  # type: ignore[misc]
    """Fails when Presidio finds PII; the fix value is Presidio's anonymised text."""

    def __init__(
        self,
        entities: list[str] | None = None,
        engines: tuple[Any, Any] | None = None,
        on_fail: Any = None,
    ) -> None:
        super().__init__(on_fail=on_fail)
        self.entities = entities
        self._engines = engines

    def validate(self, value: Any, metadata: dict[str, Any]) -> ValidationResult:
        if self._engines is None:
            self._engines = load_presidio()
        analyzer, anonymizer = self._engines
        text = str(value)
        results = analyzer.analyze(text=text, language="en", entities=self.entities)
        if not results:
            return PassResult()
        kinds = sorted({r.entity_type for r in results})
        fixed = anonymizer.anonymize(text=text, analyzer_results=results).text
        return FailResult(error_message=f"found PII: {', '.join(kinds)}", fix_value=fixed)


@register_validator(name="langchaingov/toxic_language", data_type="string")
class ToxicLanguage(Validator):  # type: ignore[misc]
    """Fails when any toxicity label scores at or above ``threshold``."""

    def __init__(
        self,
        threshold: float = 0.5,
        model: str = TOXIC_MODEL,
        classify: TextScores | None = None,
        on_fail: Any = None,
    ) -> None:
        super().__init__(on_fail=on_fail)
        self.threshold = threshold
        self.model = model
        self._classify = classify

    def validate(self, value: Any, metadata: dict[str, Any]) -> ValidationResult:
        if self._classify is None:
            self._classify = load_text_classifier(self.model)
        scores = self._classify(str(value))
        hits = {label: s for label, s in scores.items() if s >= self.threshold}
        if not hits:
            return PassResult()
        shown = ", ".join(f"{label} {score:.2f}" for label, score in sorted(hits.items()))
        return FailResult(error_message=f"toxic language: {shown}")


@register_validator(name="langchaingov/restrict_to_topic", data_type="string")
class RestrictToTopic(Validator):  # type: ignore[misc]
    """Fails unless the top zero-shot label is a valid topic at or above ``threshold``."""

    def __init__(
        self,
        valid_topics: list[str],
        invalid_topics: list[str] | None = None,
        threshold: float = 0.5,
        model: str = TOPIC_MODEL,
        classify: TopicScores | None = None,
        on_fail: Any = None,
    ) -> None:
        super().__init__(on_fail=on_fail)
        self.valid_topics = valid_topics
        self.invalid_topics = invalid_topics or []
        self.threshold = threshold
        self.model = model
        self._classify = classify

    def validate(self, value: Any, metadata: dict[str, Any]) -> ValidationResult:
        if self._classify is None:
            self._classify = load_zero_shot(self.model)
        scores = self._classify(str(value), [*self.valid_topics, *self.invalid_topics])
        top, score = max(scores.items(), key=lambda item: item[1])
        if top in self.valid_topics and score >= self.threshold:
            return PassResult()
        return FailResult(error_message=f"topic {top!r} ({score:.2f}) is not allowed")
