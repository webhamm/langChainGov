import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from langchaingov.chain import GuardedChain
from tests.fakes import RaisingChatModel, RecordingChatModel, StubGuard


def test_allow_all_calls_model_and_returns_reply() -> None:
    model = RecordingChatModel(responses=["the reply"])
    a, b = StubGuard("a"), StubGuard("b")
    result = GuardedChain(model, [a, b], system="be nice").invoke("hello")
    assert result.reply == "the reply"
    assert not result.blocked
    assert [(v.stage, v.guard, v.action) for v in result.verdicts] == [
        ("input", "a", "allow"),
        ("input", "b", "allow"),
        ("output", "a", "allow"),
        ("output", "b", "allow"),
    ]
    assert model.seen == [[SystemMessage(content="be nice"), HumanMessage(content="hello")]]


def test_input_block_stops_before_model() -> None:
    model = RaisingChatModel(responses=["x"], error=AssertionError("model must not be called"))
    first = StubGuard("first", on_input=("block", "forbidden"))
    second = StubGuard("second")
    result = GuardedChain(model, [first, second]).invoke("hello")
    assert result.blocked
    assert result.reply is None
    assert result.block_reason == "first (input): forbidden"
    assert second.calls == []


def test_modify_threads_text_to_next_guard_and_model() -> None:
    model = RecordingChatModel(responses=["ok"])
    upper = StubGuard("upper", on_input=("modify", "shouting"))
    after = StubGuard("after")
    result = GuardedChain(model, [upper, after]).invoke("hello")
    assert after.calls[0] == ("input", "HELLO")
    assert model.seen == [[HumanMessage(content="HELLO")]]
    assert result.verdicts[0].action == "modify"
    assert result.reply == "ok"


def test_output_block_withholds_reply() -> None:
    model = RecordingChatModel(responses=["secret stuff"])
    guard = StubGuard("out", on_output=("block", "leaks"))
    result = GuardedChain(model, [guard]).invoke("hello")
    assert result.blocked
    assert result.reply is None
    assert result.block_reason == "out (output): leaks"
    assert guard.calls[-1] == ("output", "secret stuff")


def test_output_modify_changes_reply() -> None:
    model = RecordingChatModel(responses=["quiet"])
    guard = StubGuard("out", on_output=("modify", "louder"))
    result = GuardedChain(model, [guard]).invoke("hello")
    assert result.reply == "QUIET"


@pytest.mark.parametrize("stage", ["input", "output"])
def test_guard_exception_fails_closed(stage: str) -> None:
    model = RecordingChatModel(responses=["ok"])
    guard = StubGuard("flaky", raise_on=stage)  # type: ignore[arg-type]
    result = GuardedChain(model, [guard]).invoke("hello")
    assert result.blocked
    verdict = result.verdicts[-1]
    assert verdict.stage == stage
    assert verdict.reason == "guard failed: RuntimeError: stub exploded"


def test_check_prompt_runs_input_guards_only() -> None:
    model = RaisingChatModel(responses=["x"], error=AssertionError("model must not be called"))
    upper = StubGuard("upper", on_input=("modify", "shouting"))
    blocker = StubGuard("blocker", on_input=("block", "no"))
    result = GuardedChain(model, [upper, blocker]).invoke("hello")
    screened = GuardedChain(model, [upper]).check_prompt("hello")
    assert screened.reply is None and not screened.blocked
    assert [(v.stage, v.action, v.text) for v in screened.verdicts] == [
        ("input", "modify", "HELLO")
    ]
    assert result.blocked and result.block_reason == "blocker (input): no"
