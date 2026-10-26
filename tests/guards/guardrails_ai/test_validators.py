import re
from dataclasses import dataclass
from typing import Any

import pytest
from guardrails import Guard, OnFailAction
from guardrails.errors import ValidationError

from langchaingov.guards.guardrails_ai.validators import DetectPii, RestrictToTopic, ToxicLanguage


@dataclass
class FakeResult:
    entity_type: str
    start: int
    end: int


class FakeAnalyzer:
    def analyze(self, text: str, language: str, entities: Any) -> list[FakeResult]:
        results = []
        for token in ("jane.doe@example.com", "555-014-2778"):
            if token in text:
                i = text.index(token)
                kind = "EMAIL_ADDRESS" if "@" in token else "PHONE_NUMBER"
                results.append(FakeResult(kind, i, i + len(token)))
        return results


class FakeAnonymized:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeAnonymizer:
    def anonymize(self, text: str, analyzer_results: list[FakeResult]) -> FakeAnonymized:
        for r in sorted(analyzer_results, key=lambda r: r.start, reverse=True):
            text = text[: r.start] + f"<{r.entity_type}>" + text[r.end :]
        return FakeAnonymized(text)


def test_detect_pii_fix() -> None:
    validator = DetectPii(engines=(FakeAnalyzer(), FakeAnonymizer()), on_fail=OnFailAction.FIX)
    out = Guard().use(validator).validate("mail jane.doe@example.com or call 555-014-2778")
    assert out.validation_passed
    assert out.validated_output == "mail <EMAIL_ADDRESS> or call <PHONE_NUMBER>"


def test_detect_pii_exception_lists_kinds() -> None:
    validator = DetectPii(
        engines=(FakeAnalyzer(), FakeAnonymizer()), on_fail=OnFailAction.EXCEPTION
    )
    with pytest.raises(ValidationError, match=re.escape("found PII: EMAIL_ADDRESS, PHONE_NUMBER")):
        Guard().use(validator).validate("jane.doe@example.com 555-014-2778")


def test_detect_pii_clean_passes() -> None:
    validator = DetectPii(engines=(FakeAnalyzer(), FakeAnonymizer()), on_fail=OnFailAction.FIX)
    out = Guard().use(validator).validate("my fern is fine")
    assert out.validation_passed and out.validated_output == "my fern is fine"


def test_toxic_threshold() -> None:
    def classify(text: str) -> dict[str, float]:
        return {
            "toxic": 0.9 if "idiot" in text else 0.05,
            "insult": 0.7 if "idiot" in text else 0.0,
        }

    toxic = ToxicLanguage(threshold=0.5, classify=classify, on_fail=OnFailAction.EXCEPTION)
    assert Guard().use(toxic).validate("nice fern").validation_passed
    with pytest.raises(ValidationError, match=re.escape("toxic language: insult 0.70, toxic 0.90")):
        Guard().use(toxic).validate("you idiot")


def test_restrict_to_topic() -> None:
    seen: list[list[str]] = []

    def classify(text: str, labels: list[str]) -> dict[str, float]:
        seen.append(labels)
        if "stocks" in text:
            return {"houseplants": 0.1, "finance": 0.8}
        if "weather" in text:
            return {"houseplants": 0.4, "finance": 0.3}
        return {"houseplants": 0.9, "finance": 0.05}

    topic = RestrictToTopic(
        ["houseplants"],
        ["finance"],
        threshold=0.5,
        classify=classify,
        on_fail=OnFailAction.EXCEPTION,
    )
    guard = Guard().use(topic)
    assert guard.validate("repot my fern").validation_passed
    with pytest.raises(ValidationError, match=re.escape("topic 'finance' (0.80) is not allowed")):
        guard.validate("buy stocks")
    with pytest.raises(
        ValidationError, match=re.escape("topic 'houseplants' (0.40) is not allowed")
    ):
        guard.validate("what's the weather")
    assert seen[0] == ["houseplants", "finance"]
