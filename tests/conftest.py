"""Shared fixtures. Every test runs in an empty temp directory with no project env vars,
so the developer's real ``.env`` is never read and no test can reach the network."""

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    for name in list(os.environ):
        if name.startswith("LANGCHAINGOV_") or name in {"LITELLM_API_KEY", "OPENAI_API_KEY"}:
            monkeypatch.delenv(name)
