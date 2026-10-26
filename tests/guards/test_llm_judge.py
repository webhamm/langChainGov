from pathlib import Path

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import SystemMessage

from langchaingov import llm
from langchaingov.guards import registry
from langchaingov.guards.custom.llm_judge import DEFAULT_RUBRIC, LlmJudge, parse_judge_reply
from langchaingov.settings import Settings
from tests.fakes import RecordingChatModel


def judge_with(reply: str) -> tuple[LlmJudge, RecordingChatModel]:
    model = RecordingChatModel(responses=[reply])
    return LlmJudge(model, rubric="- bad: anything bad"), model


def test_safe_reply_allows() -> None:
    judge, model = judge_with('{"safe": true, "category": "none", "reason": "fine"}')
    v = judge.check_input("How often should I water basil?")
    assert v.action == "allow"
    system = model.seen[0][0]
    assert isinstance(system, SystemMessage)
    assert "- bad: anything bad" in str(system.content)
    assert "Stage: input" in str(model.seen[0][1].content)
    assert "How often should I water basil?" in str(model.seen[0][1].content)


def test_unsafe_reply_blocks_with_category() -> None:
    judge, _ = judge_with('{"safe": false, "category": "bad", "reason": "it is bad"}')
    v = judge.check_output("something")
    assert v.action == "block" and v.stage == "output"
    assert v.reason == "bad: it is bad"


def test_fenced_json_is_tolerated() -> None:
    judge, _ = judge_with('Sure!\n```json\n{"safe": false, "category": "bad"}\n```')
    v = judge.check_input("x")
    assert v.action == "block"
    assert v.reason == "bad: unsafe"


def test_garbage_reply_fails_closed() -> None:
    judge, _ = judge_with("I cannot decide, sorry.")
    v = judge.check_input("x")
    assert v.action == "block"
    assert v.reason.startswith("judge reply was not valid JSON:")


@pytest.mark.parametrize("raw", ['{"safe": "maybe"}', '{"category": "x"}', "{not json}"])
def test_parse_rejects_bad_shapes(raw: str) -> None:
    assert parse_judge_reply(raw) is None


def test_factory_defaults_to_shared_model_and_builtin_rubric() -> None:
    shared = FakeListChatModel(responses=["x"])
    guard = registry.get("llm-judge", Settings(), shared)
    assert isinstance(guard, LlmJudge)
    assert guard.model is shared
    assert guard.rubric == DEFAULT_RUBRIC


def test_factory_uses_judge_model_and_rubric_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rubric = tmp_path / "rubric.txt"
    rubric.write_text("- custom: my rule\n")
    separate = FakeListChatModel(responses=["y"])
    built: list[str | None] = []

    def fake_make(settings: Settings, model: str | None = None) -> FakeListChatModel:
        built.append(model)
        return separate

    monkeypatch.setattr(llm, "make_chat_model", fake_make)
    settings = Settings(judge_model="judge-llama", judge_rubric=rubric)
    guard = registry.get("llm-judge", settings, FakeListChatModel(responses=["x"]))
    assert isinstance(guard, LlmJudge)
    assert guard.model is separate
    assert built == ["judge-llama"]
    assert guard.rubric == "- custom: my rule\n"
