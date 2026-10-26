from typing import Any

from guardrails import Guard, OnFailAction
from guardrails.classes.validation.validation_result import (
    FailResult,
    PassResult,
    ValidationResult,
)
from guardrails.validator_base import Validator, register_validator

from langchaingov.guards.guardrails_ai.adapter import GuardrailsAiGuard


@register_validator(name="langchaingov/test_no_bad", data_type="string")
class NoBad(Validator):  # type: ignore[misc]
    def validate(self, value: Any, metadata: dict[str, Any]) -> ValidationResult:
        if "bad" in value:
            return FailResult(error_message="has bad", fix_value=value.replace("bad", "***"))
        return PassResult()


def guard_with(action: OnFailAction, check_output: bool = True) -> GuardrailsAiGuard:
    return GuardrailsAiGuard("g", "d", Guard().use(NoBad(on_fail=action)), check_output)


def test_fix_is_modify() -> None:
    v = guard_with(OnFailAction.FIX).check_input("a bad day")
    assert v.action == "modify"
    assert v.text == "a *** day"
    assert v.reason == "fixed by validator"


def test_exception_is_block_with_clean_reason() -> None:
    v = guard_with(OnFailAction.EXCEPTION).check_output("a bad day")
    assert v.action == "block" and v.stage == "output"
    assert v.reason == "has bad"


def test_noop_failure_is_block() -> None:
    v = guard_with(OnFailAction.NOOP).check_input("a bad day")
    assert v.action == "block"


def test_clean_text_allows() -> None:
    v = guard_with(OnFailAction.EXCEPTION).check_input("a good day")
    assert v.action == "allow" and v.text == "a good day"


def test_output_can_be_skipped() -> None:
    v = guard_with(OnFailAction.EXCEPTION, check_output=False).check_output("a bad day")
    assert v.action == "allow"


def test_telemetry_is_disabled_even_after_building_guards() -> None:
    from guardrails.settings import settings
    from guardrails.utils.hub_telemetry_utils import HubTelemetry

    guard_with(OnFailAction.FIX).check_input("a bad day")  # builds and runs a Guard
    assert HubTelemetry()._tracer is None  # no tracer, so no spans can be exported
    assert settings.disable_tracing is True
