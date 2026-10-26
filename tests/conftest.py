"""Shared fixtures. Every test runs in an empty temp directory with no project env vars,
so the developer's real ``.env`` is never read and no test can reach the network."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from langchaingov.guards import registry


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    for name in list(os.environ):
        if name.startswith("LANGCHAINGOV_") or name in {"LITELLM_API_KEY", "OPENAI_API_KEY"}:
            monkeypatch.delenv(name)


@pytest.fixture
def clean_registry() -> Iterator[None]:
    """Run a test against an empty registry with built-ins not loaded, then restore."""
    saved = dict(registry._registry)
    saved_loaded = registry._builtins_loaded
    registry._registry.clear()
    registry._builtins_loaded = True
    try:
        yield
    finally:
        registry._registry.clear()
        registry._registry.update(saved)
        registry._builtins_loaded = saved_loaded
