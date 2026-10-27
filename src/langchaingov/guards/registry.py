"""Name-to-factory registry so the CLI and eval harness can pick guardrails by name."""

from collections.abc import Callable
from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel

from langchaingov.guards.base import Guardrail
from langchaingov.settings import Settings

GuardFactory = Callable[[Settings, BaseChatModel], Guardrail]
"""Builds a guardrail. Receives the settings and the shared chat model, so guards that
need the LLM (judges, rails) use the same instance as the chain."""


@dataclass(frozen=True)
class GuardSpec:
    name: str
    description: str
    factory: GuardFactory


class MissingExtraError(RuntimeError):
    """The guard needs an optional dependency group that is not installed."""

    def __init__(self, guard: str, extra: str) -> None:
        self.guard = guard
        self.extra = extra
        super().__init__(f"guard {guard!r} needs the {extra!r} extra: uv sync --extra {extra}")


class UnknownGuardError(KeyError):
    def __init__(self, name: str, known: list[str]) -> None:
        self.name = name
        self.known = known
        super().__init__(f"unknown guard {name!r}; known guards: {', '.join(known) or 'none'}")


_registry: dict[str, GuardSpec] = {}
_builtins_loaded = False


def register(name: str, description: str, factory: GuardFactory) -> None:
    """Register a guardrail under ``name``. Registering the same name twice is an error."""
    if name in _registry:
        raise ValueError(f"guard {name!r} is already registered")
    _registry[name] = GuardSpec(name=name, description=description, factory=factory)


def _ensure_builtins() -> None:
    global _builtins_loaded
    if _builtins_loaded:
        return
    _builtins_loaded = True
    # Imported lazily: the guard packages import this module to register themselves.
    from langchaingov.guards import custom, guardrails_ai, middleware, nemo

    custom.register_all()
    middleware.register_all()
    guardrails_ai.register_all()
    nemo.register_all()


def specs() -> list[GuardSpec]:
    _ensure_builtins()
    return sorted(_registry.values(), key=lambda s: s.name)


def names() -> list[str]:
    return [s.name for s in specs()]


def get(name: str, settings: Settings, model: BaseChatModel) -> Guardrail:
    _ensure_builtins()
    try:
        spec = _registry[name]
    except KeyError:
        raise UnknownGuardError(name, names()) from None
    return spec.factory(settings, model)
