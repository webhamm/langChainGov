from pathlib import Path

import pytest

from langchaingov.settings import Settings


def test_defaults_when_nothing_is_set() -> None:
    settings = Settings()
    assert settings.base_url == "http://localhost:4000/v1"
    assert settings.model == ""
    assert settings.api_key == ""
    assert settings.temperature == 0.0


def test_reads_prefixed_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGCHAINGOV_BASE_URL", "http://example.test:1234/v1")
    monkeypatch.setenv("LANGCHAINGOV_MODEL", "fake-llama")
    monkeypatch.setenv("LANGCHAINGOV_TEMPERATURE", "0.7")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    settings = Settings()
    assert settings.base_url == "http://example.test:1234/v1"
    assert settings.model == "fake-llama"
    assert settings.temperature == 0.7
    assert settings.api_key == "sk-test"


def test_reads_dotenv_file_in_cwd(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("LITELLM_API_KEY=sk-from-file\nLANGCHAINGOV_MODEL=file-model\n")
    settings = Settings()
    assert settings.api_key == "sk-from-file"
    assert settings.model == "file-model"


def test_accepts_litellm_master_key_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-master")
    assert Settings().api_key == "sk-master"


def test_api_key_can_be_passed_by_field_name() -> None:
    assert Settings(api_key="sk-direct").api_key == "sk-direct"
