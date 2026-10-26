"""Custom middleware written with LangChain's ``@before_model`` / ``@after_model``
decorators: the smallest possible demonstration of the hook mechanics."""

from typing import Any

from langchain.agents.middleware import AgentState, after_model, before_model
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime

from langchaingov.guards.middleware.adapter import Middleware, MiddlewareGuard
from langchaingov.llm import message_text


def make_hooks(block_phrase: str, rewrite_from: str, rewrite_to: str) -> list[Middleware]:
    """A before-model hook that ends the run when the prompt contains ``block_phrase``,
    and an after-model hook that rewrites ``rewrite_from`` to ``rewrite_to`` in the reply."""

    @before_model(can_jump_to=["end"], name="block_phrase")
    def block_phrase_hook(state: AgentState[Any], runtime: Runtime[None]) -> dict[str, Any] | None:
        for message in reversed(state["messages"]):
            if isinstance(message, HumanMessage):
                if block_phrase.lower() in message_text(message).lower():
                    return {
                        "jump_to": "end",
                        "messages": [AIMessage(content=f"prompt contains {block_phrase!r}")],
                    }
                break
        return None

    @after_model(name="rewrite_reply")
    def rewrite_reply_hook(state: AgentState[Any], runtime: Runtime[None]) -> dict[str, Any] | None:
        messages = list(state["messages"])
        for i in range(len(messages) - 1, -1, -1):
            message = messages[i]
            if isinstance(message, AIMessage):
                text = message_text(message)
                if rewrite_from.lower() not in text.lower():
                    return None
                pattern_free = _replace_case_insensitive(text, rewrite_from, rewrite_to)
                messages[i] = message.model_copy(update={"content": pattern_free})
                return {"messages": messages}
        return None

    return [block_phrase_hook, rewrite_reply_hook]


def _replace_case_insensitive(text: str, old: str, new: str) -> str:
    import re

    return re.sub(re.escape(old), new, text, flags=re.IGNORECASE)


class CustomHooksGuard(MiddlewareGuard):
    name = "lc-custom-hooks"
    description = (
        "LangChain @before_model hook that ends the run on a configured phrase, and an "
        "@after_model hook that rewrites a configured word in the reply."
    )

    def __init__(self, block_phrase: str, rewrite_from: str, rewrite_to: str) -> None:
        super().__init__(
            self.name, self.description, make_hooks(block_phrase, rewrite_from, rewrite_to)
        )
