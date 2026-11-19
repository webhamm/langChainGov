import pytest
import tiktoken

from langchaingov.golden.tokens import CharCounter, TiktokenCounter, TokenizerUnavailable


def test_char_counter_rounds_up() -> None:
    counter = CharCounter()
    assert [counter.count(t) for t in ("", "abc", "abcd", "abcde")] == [0, 1, 1, 2]


def test_tiktoken_counter_loads_lazily(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(name: str) -> tiktoken.Encoding:
        raise AssertionError("must not load at construction")

    monkeypatch.setattr(tiktoken, "get_encoding", boom)
    counter = TiktokenCounter()
    assert counter.name == "tiktoken:o200k_base"


def test_tiktoken_load_failure_is_explained(monkeypatch: pytest.MonkeyPatch) -> None:
    def offline(name: str) -> tiktoken.Encoding:
        raise ConnectionError("no network")

    monkeypatch.setattr(tiktoken, "get_encoding", offline)
    with pytest.raises(TokenizerUnavailable, match="downloads once, then caches"):
        TiktokenCounter().count("hello")
