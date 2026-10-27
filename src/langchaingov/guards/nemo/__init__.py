"""NVIDIA NeMo Guardrails (the ``nemoguardrails`` package) behind the ``Guardrail``
protocol. Installed with ``uv sync --extra nemo``."""

import importlib.util

from langchain_core.language_models import BaseChatModel

from langchaingov.guards.base import Guardrail
from langchaingov.guards.registry import MissingExtraError, register
from langchaingov.settings import Settings

EXTRA = "nemo"
GUARD_NAME = "nemo-rails"


def is_installed() -> bool:
    return importlib.util.find_spec("nemoguardrails") is not None


def _describe(text: str) -> str:
    return text if is_installed() else f"{text} [not installed: uv sync --extra {EXTRA}]"


def _factory(settings: Settings, model: BaseChatModel) -> Guardrail:
    if not is_installed():
        raise MissingExtraError(GUARD_NAME, EXTRA)
    from langchaingov.guards.nemo.adapter import NemoRailsGuard

    return NemoRailsGuard.from_settings(settings)


def register_all() -> None:
    register(
        GUARD_NAME,
        _describe(
            "NeMo Guardrails Colang 2 rails: self-check input and output prompts, and an "
            "off-topic rail of Colang intent flows; the rails call the model themselves."
        ),
        _factory,
    )
