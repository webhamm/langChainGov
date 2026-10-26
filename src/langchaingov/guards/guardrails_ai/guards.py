"""Build the three Guardrails AI guards from settings."""

from guardrails import Guard, OnFailAction

from langchaingov.guards.guardrails_ai.adapter import GuardrailsAiGuard
from langchaingov.guards.guardrails_ai.validators import DetectPii, RestrictToTopic, ToxicLanguage
from langchaingov.settings import Settings


def make_pii_guard(settings: Settings) -> GuardrailsAiGuard:
    on_fail = OnFailAction.FIX if settings.pii_mode == "redact" else OnFailAction.EXCEPTION
    validator = DetectPii(entities=settings.gr_pii_entity_list(), on_fail=on_fail)
    return GuardrailsAiGuard("gr-pii", "Guardrails AI + Presidio PII", Guard().use(validator))


def make_toxic_guard(settings: Settings) -> GuardrailsAiGuard:
    validator = ToxicLanguage(threshold=settings.gr_toxic_threshold, on_fail=OnFailAction.EXCEPTION)
    return GuardrailsAiGuard("gr-toxic", "Guardrails AI toxicity", Guard().use(validator))


def make_topic_guard(settings: Settings) -> GuardrailsAiGuard:
    validator = RestrictToTopic(
        valid_topics=settings.gr_valid_topic_list(),
        invalid_topics=settings.gr_invalid_topic_list(),
        threshold=settings.gr_topic_threshold,
        on_fail=OnFailAction.EXCEPTION,
    )
    return GuardrailsAiGuard(
        "gr-topic", "Guardrails AI topic", Guard().use(validator), check_output=False
    )
