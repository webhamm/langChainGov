from langchaingov.guards.base import Stage
from langchaingov.guards.middleware.hitl import HumanInTheLoop


def test_no_policy_blocks_with_reason() -> None:
    v = HumanInTheLoop(None).check_input("sell me a fern")
    assert v.action == "block"
    assert v.reason == "no human available to approve the input"


def test_policy_approves() -> None:
    asked: list[tuple[str, Stage]] = []

    def policy(text: str, stage: Stage) -> bool:
        asked.append((text, stage))
        return True

    v = HumanInTheLoop(policy).check_input("sell me a fern")
    assert v.action == "allow"
    assert asked == [("sell me a fern", "input")]


def test_policy_rejects() -> None:
    v = HumanInTheLoop(lambda text, stage: False).check_input("sell me a fern")
    assert v.action == "block"
    assert v.reason == "rejected by human reviewer"


def test_each_call_is_a_fresh_review() -> None:
    answers = iter([True, False])
    guard = HumanInTheLoop(lambda text, stage: next(answers))
    assert guard.check_input("one").action == "allow"
    assert guard.check_input("two").action == "block"


def test_output_is_not_reviewed() -> None:
    v = HumanInTheLoop(None).check_output("reply")
    assert v.action == "allow"
