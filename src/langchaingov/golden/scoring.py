"""Deterministic needle-recall scoring. No model judges the answers, so the measurement
itself can never drift."""

import re

from pydantic import BaseModel

from langchaingov.golden.models import Needle

_NOT_WORD = re.compile(r"[\W_]+")


class NeedleScores(BaseModel):
    recalled: dict[str, bool]
    recall: float
    """Fraction of needles recalled, 0 to 1."""


def normalize(text: str) -> str:
    """Casefold, turn punctuation into spaces, collapse whitespace."""
    return " ".join(_NOT_WORD.sub(" ", text.casefold()).split())


def score(response: str, needles: list[Needle]) -> NeedleScores:
    """A needle is recalled when its normalized answer appears in the normalized response
    as whole words, anywhere in the reply (so "4817" does not match "48170")."""
    haystack = f" {normalize(response)} "
    recalled = {n.id: f" {normalize(n.answer)} " in haystack for n in needles}
    return NeedleScores(recalled=recalled, recall=sum(recalled.values()) / len(needles))
