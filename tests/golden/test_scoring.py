import pytest

from langchaingov.golden.loader import load_set
from langchaingov.golden.scoring import normalize, score

NEEDLES = load_set(None).needles
PERFECT = (
    "vault-door: heron blue\n"
    "ferry-captain: Ilsabet Morrow\n"
    "logbook-page: 4817\n"
    "orchard-password: copper finch\n"
    "flood-month: Brumewane"
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("  Heron   BLUE. ", "heron blue"),
        ("logbook-page: 4,817!", "logbook page 4 817"),
        ("copper_finch", "copper finch"),
        ("", ""),
    ],
)
def test_normalize(text: str, expected: str) -> None:
    assert normalize(text) == expected


def test_perfect_reply_recalls_everything() -> None:
    result = score(PERFECT, NEEDLES)
    assert result.recall == 1.0
    assert all(result.recalled.values())


def test_answers_count_anywhere_in_any_format() -> None:
    reply = "The door is Heron Blue; the password is 'Copper Finch'."
    result = score(reply, NEEDLES)
    assert result.recalled == {
        "vault-door": True,
        "ferry-captain": False,
        "logbook-page": False,
        "orchard-password": True,
        "flood-month": False,
    }
    assert result.recall == pytest.approx(0.4)


@pytest.mark.parametrize("reply", ["page 48170", "page 14817", "brumewanes", "heron-blueish"])
def test_partial_words_do_not_count(reply: str) -> None:
    assert score(reply, NEEDLES).recall == 0.0


def test_empty_reply_recalls_nothing() -> None:
    result = score("", NEEDLES)
    assert result.recall == 0.0
    assert set(result.recalled) == {n.id for n in NEEDLES}
