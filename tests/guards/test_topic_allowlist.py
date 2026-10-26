import pytest

from langchaingov.guards.custom.topic_allowlist import TopicAllowlist
from langchaingov.settings import Settings


@pytest.fixture
def guard() -> TopicAllowlist:
    return TopicAllowlist(["plant", "fern", "grow light", "cactus", "cacti", "", " "])


def test_allows_on_topic_including_plurals(guard: TopicAllowlist) -> None:
    assert guard.check_input("My ferns look sad.").action == "allow"
    assert guard.check_input("Which GROW LIGHT should I buy?").action == "allow"
    assert guard.check_input("Do cacti need sun?").action == "allow"


def test_blocks_off_topic_with_reason(guard: TopicAllowlist) -> None:
    v = guard.check_input("Which stocks should I buy this week?")
    assert v.action == "block"
    assert v.stage == "input"
    assert v.reason == "mentions no allowed topic (allowed: plant, fern, grow light, cactus, cacti)"


def test_partial_words_do_not_count(guard: TopicAllowlist) -> None:
    assert guard.check_input("Explain implanted devices.").action == "block"


def test_output_is_never_checked(guard: TopicAllowlist) -> None:
    v = guard.check_output("Here is a stock tip.")
    assert v.action == "allow" and v.stage == "output"


def test_reason_truncates_long_lists() -> None:
    guard = TopicAllowlist([f"t{i}" for i in range(10)])
    assert guard.check_input("nothing").reason.endswith("t5, ...)")


def test_empty_list_blocks_everything() -> None:
    assert TopicAllowlist([]).check_input("plants").action == "block"


def test_settings_topics_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGCHAINGOV_TOPICS", "a, b c ,")
    assert Settings().topic_words() == ["a", "b c"]


def test_settings_topics_default_is_about_plants() -> None:
    assert "plant" in Settings().topic_words()
