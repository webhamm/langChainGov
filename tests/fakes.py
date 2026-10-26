"""Fake chat models and guards shared by the tests. Nothing here touches the network."""

from typing import Any

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from pydantic import Field

from langchaingov.guards.base import Stage, Verdict


class RecordingChatModel(FakeListChatModel):
    """A fake that remembers the messages it was invoked with."""

    seen: list[list[BaseMessage]] = Field(default_factory=list)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.seen.append(list(messages))
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


class RaisingChatModel(FakeListChatModel):
    """A fake whose invocation raises a given exception."""

    error: Exception

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise self.error


class StubGuard:
    """A guard whose verdicts are chosen per stage.

    ``on_input`` / ``on_output`` are ``("allow" | "block" | "modify", reason)``; for modify
    the text is upper-cased so tests can see it flow through. ``raise_on`` makes the guard
    raise at that stage instead.
    """

    def __init__(
        self,
        name: str = "stub",
        on_input: tuple[str, str] = ("allow", ""),
        on_output: tuple[str, str] = ("allow", ""),
        raise_on: Stage | None = None,
    ) -> None:
        self.name = name
        self.description = f"stub guard {name}"
        self.on_input = on_input
        self.on_output = on_output
        self.raise_on = raise_on
        self.calls: list[tuple[Stage, str]] = []

    def check_input(self, text: str) -> Verdict:
        return self._verdict("input", text, self.on_input)

    def check_output(self, text: str) -> Verdict:
        return self._verdict("output", text, self.on_output)

    def _verdict(self, stage: Stage, text: str, spec: tuple[str, str]) -> Verdict:
        self.calls.append((stage, text))
        if self.raise_on == stage:
            raise RuntimeError("stub exploded")
        action, reason = spec
        if action == "allow":
            return Verdict.allow(self.name, stage, text)
        if action == "modify":
            return Verdict.modify(self.name, stage, text.upper(), reason)
        return Verdict.block(self.name, stage, text, reason)
