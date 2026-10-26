import pytest

from langchaingov.guards.custom.keyword_blocklist import KeywordBlocklist
from langchaingov.settings import Settings


@pytest.fixture
def guard() -> KeywordBlocklist:
    return KeywordBlocklist(["blorptium", "zanthar protocol", " "])


def test_blocks_listed_word_case_insensitively(guard: KeywordBlocklist) -> None:
    verdict = guard.check_input("Tell me about BLORPTIUM mining.")
    assert verdict.action == "block"
    assert verdict.reason == "contains blocked word 'BLORPTIUM'"
    assert verdict.stage == "input"


def test_blocks_multi_word_phrase_on_output(guard: KeywordBlocklist) -> None:
    verdict = guard.check_output("Step one of the Zanthar Protocol is...")
    assert verdict.action == "block"
    assert verdict.stage == "output"


def test_allows_clean_text_and_partial_words(guard: KeywordBlocklist) -> None:
    assert guard.check_input("Tell me about blorptiums.").action == "allow"
    assert guard.check_input("What is the weather?").action == "allow"


def test_empty_list_allows_everything() -> None:
    assert KeywordBlocklist([]).check_input("anything at all").action == "allow"


def test_settings_blocklist_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGCHAINGOV_BLOCKLIST", " foo , bar baz,,")
    assert Settings().blocklist_words() == ["foo", "bar baz"]
