"""The one protocol every guardrail implements, and the verdicts it produces."""

from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, model_validator

Action = Literal["allow", "block", "modify"]
Stage = Literal["input", "output"]


class Verdict(BaseModel):
    """What one guardrail decided about one piece of text.

    ``text`` is the text to continue with: unchanged for ``allow``, rewritten for
    ``modify``, and the offending text for ``block`` (so a reader can see what tripped).
    """

    guard: str
    stage: Stage
    action: Action
    text: str
    reason: str = ""

    @model_validator(mode="after")
    def _reason_required_unless_allowed(self) -> "Verdict":
        if self.action != "allow" and not self.reason.strip():
            raise ValueError(f"a {self.action!r} verdict needs a reason")
        return self

    @classmethod
    def allow(cls, guard: str, stage: Stage, text: str) -> "Verdict":
        return cls(guard=guard, stage=stage, action="allow", text=text)

    @classmethod
    def block(cls, guard: str, stage: Stage, text: str, reason: str) -> "Verdict":
        return cls(guard=guard, stage=stage, action="block", text=text, reason=reason)

    @classmethod
    def modify(cls, guard: str, stage: Stage, text: str, reason: str) -> "Verdict":
        return cls(guard=guard, stage=stage, action="modify", text=text, reason=reason)


class GuardedResult(BaseModel):
    """The outcome of one guarded model call."""

    prompt: str
    reply: str | None
    """The model's reply after output guards, or ``None`` when something was blocked."""

    verdicts: list[Verdict]

    @property
    def blocked(self) -> bool:
        return any(v.action == "block" for v in self.verdicts)

    @property
    def block_reason(self) -> str | None:
        for v in self.verdicts:
            if v.action == "block":
                return f"{v.guard} ({v.stage}): {v.reason}"
        return None


@runtime_checkable
class Guardrail(Protocol):
    """A named check applied to the prompt before the model and to the reply after it."""

    name: str
    description: str

    def check_input(self, text: str) -> Verdict: ...

    def check_output(self, text: str) -> Verdict: ...
