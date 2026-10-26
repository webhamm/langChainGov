import pytest

from langchaingov.guards.base import GuardedResult, Guardrail, Verdict
from tests.fakes import StubGuard


def test_allow_needs_no_reason() -> None:
    v = Verdict.allow("g", "input", "hi")
    assert v.action == "allow" and v.reason == "" and v.text == "hi"


@pytest.mark.parametrize("action", ["block", "modify"])
def test_block_and_modify_require_a_reason(action: str) -> None:
    with pytest.raises(ValueError, match="needs a reason"):
        Verdict(guard="g", stage="input", action=action, text="hi", reason="  ")  # type: ignore[arg-type]


def test_result_blocked_and_reason() -> None:
    verdicts = [
        Verdict.allow("a", "input", "hi"),
        Verdict.block("b", "output", "bad", reason="nope"),
    ]
    result = GuardedResult(prompt="hi", reply=None, verdicts=verdicts)
    assert result.blocked
    assert result.block_reason == "b (output): nope"


def test_result_not_blocked() -> None:
    result = GuardedResult(prompt="hi", reply="ok", verdicts=[Verdict.allow("a", "input", "hi")])
    assert not result.blocked
    assert result.block_reason is None


def test_stub_guard_satisfies_protocol() -> None:
    assert isinstance(StubGuard(), Guardrail)
