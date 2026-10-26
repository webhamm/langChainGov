"""Guardrails AI (the ``guardrails-ai`` package) behind the ``Guardrail`` protocol.

Installed with ``uv sync --extra guardrails-ai``. Without it the guards are listed as
not installed and refuse to build with a hint.
"""

import importlib.util

from langchain_core.language_models import BaseChatModel

from langchaingov.guards.base import Guardrail
from langchaingov.guards.registry import GuardFactory, MissingExtraError, register
from langchaingov.settings import Settings

EXTRA = "guardrails-ai"


def is_installed() -> bool:
    return importlib.util.find_spec("guardrails") is not None


def _describe(text: str) -> str:
    return text if is_installed() else f"{text} [not installed: uv sync --extra {EXTRA}]"


def _factory(guard_name: str, builder_name: str) -> GuardFactory:
    """A registry factory that imports the heavy modules only when the guard is built."""

    def factory(settings: Settings, model: BaseChatModel) -> Guardrail:
        if not is_installed():
            raise MissingExtraError(guard_name, EXTRA)
        from langchaingov.guards.guardrails_ai import guards

        builder = getattr(guards, builder_name)
        guard: Guardrail = builder(settings)
        return guard

    return factory


def register_all() -> None:
    register(
        "gr-pii",
        _describe(
            "Guardrails AI validator on Presidio: finds PII entities and anonymises them "
            "(<EMAIL_ADDRESS> ...) or blocks; input and output."
        ),
        _factory("gr-pii", "make_pii_guard"),
    )
    register(
        "gr-toxic",
        _describe(
            "Guardrails AI validator on a local transformers toxicity classifier; "
            "blocks above a threshold; input and output."
        ),
        _factory("gr-toxic", "make_toxic_guard"),
    )
    register(
        "gr-topic",
        _describe(
            "Guardrails AI validator on a local zero-shot topic classifier; blocks prompts "
            "whose top topic is not allowed; input only."
        ),
        _factory("gr-topic", "make_topic_guard"),
    )
