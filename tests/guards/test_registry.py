import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from langchaingov.guards import registry
from langchaingov.settings import Settings
from tests.fakes import StubGuard


def test_builtins_are_registered() -> None:
    assert "keyword-blocklist" in registry.names()


def test_register_get_and_names(clean_registry: None) -> None:
    registry.register("zeta", "last", lambda s, m: StubGuard("zeta"))
    registry.register("alpha", "first", lambda s, m: StubGuard("alpha"))
    assert registry.names() == ["alpha", "zeta"]
    guard = registry.get("zeta", Settings(), FakeListChatModel(responses=["x"]))
    assert guard.name == "zeta"


def test_duplicate_registration_is_an_error(clean_registry: None) -> None:
    registry.register("dup", "one", lambda s, m: StubGuard("dup"))
    with pytest.raises(ValueError, match="already registered"):
        registry.register("dup", "two", lambda s, m: StubGuard("dup"))


def test_unknown_guard(clean_registry: None) -> None:
    registry.register("known", "k", lambda s, m: StubGuard("known"))
    with pytest.raises(
        registry.UnknownGuardError, match="unknown guard 'nope'; known guards: known"
    ):
        registry.get("nope", Settings(), FakeListChatModel(responses=["x"]))
