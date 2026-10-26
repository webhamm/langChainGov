"""Guardrails built from LangChain 1.x agent middleware and LangGraph interrupts."""

from langchaingov.guards.middleware import hitl
from langchaingov.guards.middleware.hitl import HumanInTheLoop
from langchaingov.guards.middleware.hooks import CustomHooksGuard
from langchaingov.guards.middleware.pii import LangChainPii
from langchaingov.guards.registry import register


def register_all() -> None:
    register(
        LangChainPii.name,
        LangChainPii.description,
        lambda settings, model: LangChainPii(settings.pii_mode),
    )
    register(
        HumanInTheLoop.name,
        HumanInTheLoop.description,
        lambda settings, model: HumanInTheLoop(hitl.default_policy),
    )
    register(
        CustomHooksGuard.name,
        CustomHooksGuard.description,
        lambda settings, model: CustomHooksGuard(
            settings.hooks_block_phrase, settings.hooks_rewrite_from, settings.hooks_rewrite_to
        ),
    )
