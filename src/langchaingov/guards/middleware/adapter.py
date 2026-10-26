"""Run LangChain ``AgentMiddleware`` hooks through the ``Guardrail`` protocol.

LangChain 1.x middleware exposes ``before_model`` and ``after_model`` hooks that the
agent loop calls around each model call. This adapter calls those same hooks directly
on a one-message synthetic agent state, so the middleware's own code decides, but no
agent loop or model call is involved. A hook can:

- return ``None``: nothing to do (allow);
- return ``{"messages": [...]}`` with a rewritten message (modify);
- return ``{"jump_to": "end", ...}`` to stop the run (block);
- raise one of ``block_on`` (for example ``PIIDetectionError``) (block).
"""

from collections.abc import Sequence
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.runtime import Runtime

from langchaingov.guards.base import Stage, Verdict
from langchaingov.llm import message_text

Middleware = AgentMiddleware[Any, Any, Any]


class MiddlewareGuard:
    def __init__(
        self,
        name: str,
        description: str,
        middlewares: Sequence[Middleware],
        block_on: tuple[type[Exception], ...] = (),
    ) -> None:
        self.name = name
        self.description = description
        self.middlewares = list(middlewares)
        self.block_on = block_on
        self._runtime: Runtime[Any] = Runtime()

    def check_input(self, text: str) -> Verdict:
        return self._run("input", text)

    def check_output(self, text: str) -> Verdict:
        return self._run("output", text)

    def _run(self, stage: Stage, text: str) -> Verdict:
        current = text
        modified_by: list[str] = []
        for middleware in self.middlewares:
            state = self._state(stage, current)
            try:
                hook = middleware.before_model if stage == "input" else middleware.after_model
                update = hook(state, self._runtime)
            except self.block_on as exc:
                return Verdict.block(
                    self.name, stage, current, reason=f"{_label(middleware)}: {exc}"
                )
            if not update:
                continue
            if update.get("jump_to") == "end":
                note = _last_text(update.get("messages"), AIMessage) or "middleware ended the run"
                return Verdict.block(
                    self.name, stage, current, reason=f"{_label(middleware)}: {note}"
                )
            kind = HumanMessage if stage == "input" else AIMessage
            new_text = _last_text(update.get("messages"), kind)
            if new_text is not None and new_text != current:
                current = new_text
                modified_by.append(_label(middleware))
        if modified_by:
            return Verdict.modify(
                self.name, stage, current, reason=f"rewritten by {', '.join(modified_by)}"
            )
        return Verdict.allow(self.name, stage, text)

    @staticmethod
    def _state(stage: Stage, text: str) -> dict[str, Any]:
        if stage == "input":
            return {"messages": [HumanMessage(content=text)]}
        return {"messages": [HumanMessage(content="(prompt)"), AIMessage(content=text)]}


def _label(middleware: Middleware) -> str:
    return getattr(middleware, "name", None) or type(middleware).__name__


def _last_text(messages: Any, kind: type[BaseMessage]) -> str | None:
    if not isinstance(messages, list):
        return None
    for message in reversed(messages):
        if isinstance(message, kind):
            return message_text(message)
    return None
