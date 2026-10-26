"""Human-in-the-loop on the prompt, built on LangGraph's ``interrupt`` primitive.

LangChain's built-in ``HumanInTheLoopMiddleware`` approves *tool calls*, so with a
chat that has no tools it never fires. This guard uses the same mechanism it is built
on: a graph node calls ``interrupt(payload)``, the run pauses with the payload in
``__interrupt__``, a human (or a policy) answers, and the run resumes with
``Command(resume=answer)``. When no policy is available (``guard eval``, tests), an
unanswered interrupt is a block, so the eval shows which cases would have needed a
human.
"""

import uuid
from collections.abc import Callable
from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from langchaingov.guards.base import Stage, Verdict

Policy = Callable[[str, Stage], bool]
"""Answers an interrupt: ``True`` approves the text for that stage."""

default_policy: Policy | None = None
"""Set by the CLI's ``guard run`` to ask in the terminal; ``None`` means auto-block."""


class ReviewState(TypedDict, total=False):
    text: str
    stage: str
    approved: bool


def _ask_human(state: ReviewState) -> ReviewState:
    answer = interrupt({"text": state["text"], "stage": state["stage"]})
    return {"approved": bool(answer)}


def build_review_graph() -> Any:
    graph: StateGraph[ReviewState] = StateGraph(ReviewState)
    graph.add_node("ask_human", _ask_human)
    graph.add_edge(START, "ask_human")
    graph.add_edge("ask_human", END)
    return graph.compile(checkpointer=MemorySaver())


class HumanInTheLoop:
    name = "lc-hitl"
    description = (
        "Pauses with a LangGraph interrupt before the model sees the prompt and asks a "
        "human (terminal) or a policy; unanswered means blocked."
    )

    def __init__(self, policy: Policy | None) -> None:
        self.policy = policy
        self._graph = build_review_graph()

    def check_input(self, text: str) -> Verdict:
        return self._review(text, "input")

    def check_output(self, text: str) -> Verdict:
        return Verdict.allow(self.name, "output", text)

    def _review(self, text: str, stage: Stage) -> Verdict:
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        paused = self._graph.invoke({"text": text, "stage": stage}, config)
        interrupts = paused.get("__interrupt__", [])
        if not interrupts:
            return Verdict.block(self.name, stage, text, reason="review graph did not pause")
        payload = interrupts[0].value
        if self.policy is None:
            return Verdict.block(
                self.name,
                stage,
                text,
                reason=f"no human available to approve the {payload['stage']}",
            )
        answer = self.policy(payload["text"], stage)
        resumed = self._graph.invoke(Command(resume=answer), config)
        if resumed.get("approved"):
            return Verdict.allow(self.name, stage, text)
        return Verdict.block(self.name, stage, text, reason="rejected by human reviewer")
