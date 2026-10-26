from typing import ClassVar

import pytest

from langchaingov.guards.guardrails_ai import guards, validators
from langchaingov.settings import Settings


def test_pii_guard_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        validators,
        "load_presidio",
        lambda: (_Analyzer(), _Anonymizer()),
    )
    redact = guards.make_pii_guard(Settings(pii_mode="redact"))
    v = redact.check_input("mail jane.doe@example.com")
    assert v.action == "modify" and v.text == "mail <EMAIL_ADDRESS>"

    block = guards.make_pii_guard(Settings(pii_mode="block"))
    v = block.check_output("mail jane.doe@example.com")
    assert v.action == "block" and v.reason == "found PII: EMAIL_ADDRESS"
    assert _Analyzer.seen_entities[-1] == Settings().gr_pii_entity_list()
    assert "PERSON" not in Settings().gr_pii_entity_list()

    custom = guards.make_pii_guard(Settings(gr_pii_entities="PERSON, EMAIL_ADDRESS"))
    custom.check_input("hello")
    assert _Analyzer.seen_entities[-1] == ["PERSON", "EMAIL_ADDRESS"]


def test_toxic_and_topic_guards_use_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        validators, "load_text_classifier", lambda model: lambda text: {"toxic": 0.6}
    )
    monkeypatch.setattr(
        validators,
        "load_zero_shot",
        lambda model: lambda text, labels: {labels[0]: 0.2, labels[-1]: 0.7},
    )
    toxic = guards.make_toxic_guard(Settings(gr_toxic_threshold=0.7))
    assert toxic.check_input("hmm").action == "allow"
    toxic = guards.make_toxic_guard(Settings(gr_toxic_threshold=0.5))
    assert toxic.check_output("hmm").action == "block"

    topic = guards.make_topic_guard(Settings(gr_valid_topics="plants", gr_invalid_topics="taxes"))
    v = topic.check_input("anything")
    assert v.action == "block" and v.reason == "topic 'taxes' (0.70) is not allowed"
    assert topic.check_output("anything").action == "allow"


class _Result:
    def __init__(self, start: int, end: int) -> None:
        self.entity_type = "EMAIL_ADDRESS"
        self.start = start
        self.end = end


class _Analyzer:
    seen_entities: ClassVar[list[object]] = []

    def analyze(self, text: str, language: str, entities: object) -> list[_Result]:
        self.seen_entities.append(entities)
        token = "jane.doe@example.com"
        if token not in text:
            return []
        i = text.index(token)
        return [_Result(i, i + len(token))]


class _Anonymized:
    def __init__(self, text: str) -> None:
        self.text = text


class _Anonymizer:
    def anonymize(self, text: str, analyzer_results: list[_Result]) -> _Anonymized:
        for r in analyzer_results:
            text = text[: r.start] + "<EMAIL_ADDRESS>" + text[r.end :]
        return _Anonymized(text)
