"""Schema of a golden set, a model profile, and a generated payload."""

import itertools

from pydantic import BaseModel, Field, field_validator, model_validator


class Needle(BaseModel):
    """One planted fact, the question that asks for it, and the expected answer."""

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    fact: str
    question: str
    answer: str
    depth: float = Field(ge=0.0, le=1.0)
    """Where the fact goes in the filler: 0 is the start, 1 the end."""

    @model_validator(mode="after")
    def _answer_is_in_fact_only(self) -> "Needle":
        answer = self.answer.casefold()
        if answer not in self.fact.casefold():
            raise ValueError(f"needle {self.id!r}: answer must appear in its fact")
        if answer in self.question.casefold():
            raise ValueError(f"needle {self.id!r}: the question must not contain the answer")
        return self


class GoldenSet(BaseModel):
    name: str
    description: str = ""
    generator_version: int = Field(ge=1)
    """Bump whenever a change alters payload bytes, so runs of different tests never mix."""
    seed: int
    fill_levels: list[float] = Field(min_length=1)
    output_reserve_tokens: int = Field(gt=0)
    """Tokens left free for the model's answer."""
    system: str
    instruction: str
    """Printed after the document, before the questions."""
    needles: list[Needle] = Field(min_length=1)

    @field_validator("fill_levels")
    @classmethod
    def _levels_ascending_in_range(cls, levels: list[float]) -> list[float]:
        if any(not 0.0 < level <= 1.0 for level in levels):
            raise ValueError("fill levels must be in (0, 1]")
        if any(a >= b for a, b in itertools.pairwise(levels)):
            raise ValueError("fill levels must be strictly ascending")
        return levels

    @field_validator("needles")
    @classmethod
    def _unique_ids(cls, needles: list[Needle]) -> list[Needle]:
        seen: set[str] = set()
        for needle in needles:
            if needle.id in seen:
                raise ValueError(f"duplicate needle id {needle.id!r}")
            seen.add(needle.id)
        return needles


class ModelProfile(BaseModel):
    """The context window a model is actually served with, and whether it runs locally."""

    name: str
    context_tokens: int = Field(gt=0)
    local: bool = False
    supports_seed: bool = False
    """Whether the provider honours a request ``seed``; only then does ``golden run`` send one."""


class Payload(BaseModel):
    """One generated prompt and the facts needed to check and compare it."""

    case_id: str
    """``L`` plus the fill level in percent, e.g. ``L050``."""
    level: float
    target_tokens: int
    est_tokens: int
    """The whole prompt, counted with the counter named in the build."""
    chars: int
    sha256: str
    needle_depths: dict[str, float]
    """Where each needle actually landed, as a fraction of the document's characters."""
    paragraphs: int
    """Filler paragraphs in the document (needles not included)."""
    prompt: str = Field(exclude=True, repr=False)
