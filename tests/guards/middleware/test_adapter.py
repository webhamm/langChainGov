from typing import Any

import pytest
from langchain.agents.middleware import AgentState, after_model, before_model
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime

from langchaingov.guards.middleware.adapter import MiddlewareGuard
from langchaingov.llm import message_text


class Boom(Exception):
    pass


@before_model(name="noop")
def noop(state: AgentState[Any], runtime: Runtime[None]) -> dict[str, Any] | None:
    return None


@before_model(name="upper")
def upper(state: AgentState[Any], runtime: Runtime[None]) -> dict[str, Any] | None:
    msg = state["messages"][-1]
    return {"messages": [msg.model_copy(update={"content": message_text(msg).upper()})]}


@before_model(can_jump_to=["end"], name="ender")
def ender(state: AgentState[Any], runtime: Runtime[None]) -> dict[str, Any] | None:
    if "stop" in message_text(state["messages"][-1]).lower():
        return {"jump_to": "end", "messages": [AIMessage(content="told to stop")]}
    return None


@before_model(name="raiser")
def raiser(state: AgentState[Any], runtime: Runtime[None]) -> dict[str, Any] | None:
    raise Boom("kaboom")


@after_model(name="exclaim")
def exclaim(state: AgentState[Any], runtime: Runtime[None]) -> dict[str, Any] | None:
    msgs = list(state["messages"])
    msgs[-1] = msgs[-1].model_copy(update={"content": message_text(msgs[-1]) + "!"})
    return {"messages": msgs}


def test_none_update_allows() -> None:
    v = MiddlewareGuard("g", "d", [noop]).check_input("hi")
    assert v.action == "allow" and v.text == "hi"


def test_rewritten_message_is_modify_and_threads() -> None:
    v = MiddlewareGuard("g", "d", [upper, noop]).check_input("hi there")
    assert v.action == "modify"
    assert v.text == "HI THERE"
    assert v.reason == "rewritten by upper"


def test_jump_to_end_is_block_with_note() -> None:
    v = MiddlewareGuard("g", "d", [upper, ender]).check_input("please stop")
    assert v.action == "block"
    assert v.reason == "ender: told to stop"
    assert v.text == "PLEASE STOP"


def test_listed_exception_is_block() -> None:
    v = MiddlewareGuard("g", "d", [raiser], block_on=(Boom,)).check_input("x")
    assert v.action == "block"
    assert v.reason == "raiser: kaboom"


def test_unlisted_exception_propagates() -> None:
    with pytest.raises(Boom):
        MiddlewareGuard("g", "d", [raiser]).check_input("x")


def test_output_uses_after_model_hooks() -> None:
    guard = MiddlewareGuard("g", "d", [exclaim, upper])
    v = guard.check_output("fine")
    assert v.stage == "output"
    assert v.action == "modify"
    assert v.text == "fine!"  # `upper` is a before_model hook and does not run on output


def test_state_shapes() -> None:
    assert [type(m) for m in MiddlewareGuard._state("input", "x")["messages"]] == [HumanMessage]
    assert [type(m) for m in MiddlewareGuard._state("output", "x")["messages"]] == [
        HumanMessage,
        AIMessage,
    ]
