from typing import Any

import pytest
from pydantic import ValidationError

from langchaingov.golden.models import GoldenSet, Needle


def needle(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": "vault-door",
        "fact": "The vault door is painted heron blue.",
        "question": "What color is the vault door?",
        "answer": "heron blue",
        "depth": 0.5,
    }
    return {**base, **overrides}


def golden(**overrides: Any) -> dict[str, Any]:
    base = {
        "name": "t",
        "generator_version": 1,
        "seed": 1,
        "fill_levels": [0.25, 0.5],
        "output_reserve_tokens": 100,
        "system": "s",
        "instruction": "answer",
        "needles": [needle()],
    }
    return {**base, **overrides}


def test_valid_set_parses() -> None:
    assert GoldenSet.model_validate(golden()).needles[0].id == "vault-door"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"answer": "red"}, "answer must appear in its fact"),
        ({"question": "Is it heron blue?"}, "must not contain the answer"),
        ({"depth": 1.5}, "less than or equal to 1"),
        ({"id": "Bad Id"}, "should match pattern"),
    ],
)
def test_needle_validation(overrides: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        Needle.model_validate(needle(**overrides))


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"fill_levels": [0.5, 0.25]}, "strictly ascending"),
        ({"fill_levels": [0.0, 0.5]}, r"in \(0, 1\]"),
        ({"fill_levels": [0.5, 1.2]}, r"in \(0, 1\]"),
        ({"fill_levels": []}, "at least 1"),
        ({"needles": [needle(), needle()]}, "duplicate needle id"),
        ({"needles": []}, "at least 1"),
        ({"output_reserve_tokens": 0}, "greater than 0"),
    ],
)
def test_set_validation(overrides: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        GoldenSet.model_validate(golden(**overrides))
