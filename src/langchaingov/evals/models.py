"""Schema of an eval case set."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Expected = Literal["allow", "block"]


class EvalCase(BaseModel):
    id: str
    prompt: str
    expected: Expected
    tags: list[str] = Field(default_factory=list)

    @field_validator("id", "prompt")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class EvalSet(BaseModel):
    name: str
    description: str = ""
    cases: list[EvalCase] = Field(min_length=1)

    @field_validator("cases")
    @classmethod
    def _unique_ids(cls, cases: list[EvalCase]) -> list[EvalCase]:
        seen: set[str] = set()
        for case in cases:
            if case.id in seen:
                raise ValueError(f"duplicate case id {case.id!r}")
            seen.add(case.id)
        return cases

    def filtered(self, tags: list[str] | None) -> list[EvalCase]:
        """Cases carrying any of ``tags``; all cases when ``tags`` is empty or ``None``."""
        if not tags:
            return list(self.cases)
        wanted = set(tags)
        return [c for c in self.cases if wanted & set(c.tags)]
