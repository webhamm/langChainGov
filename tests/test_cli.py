import json
from collections.abc import Sequence
from typing import Any

import httpx2
import openai
import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from typer.testing import CliRunner

from langchaingov import __version__, cli
from langchaingov.llm import message_text
from langchaingov.settings import Settings
from tests.fakes import RaisingChatModel, RecordingChatModel

runner = CliRunner()


def install_fake(
    monkeypatch: pytest.MonkeyPatch, fake: BaseChatModel
) -> list[tuple[Settings, str | None]]:
    calls: list[tuple[Settings, str | None]] = []

    def factory(settings: Settings, model: str | None) -> BaseChatModel:
        calls.append((settings, model))
        return fake

    monkeypatch.setattr(cli, "model_factory", factory)
    return calls


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    monkeypatch.setenv("LANGCHAINGOV_MODEL", "fake-llama")


def test_version_command() -> None:
    result = runner.invoke(cli.app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_chat_prints_reply(monkeypatch: pytest.MonkeyPatch, configured: None) -> None:
    fake = RecordingChatModel(responses=["Hello from the fake."])
    calls = install_fake(monkeypatch, fake)
    result = runner.invoke(cli.app, ["chat", "hi there"])
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == "Hello from the fake."
    assert calls[0][1] == "fake-llama"
    assert fake.seen == [[HumanMessage(content="hi there")]]


def test_chat_passes_system_prompt(monkeypatch: pytest.MonkeyPatch, configured: None) -> None:
    fake = RecordingChatModel(responses=["ok"])
    install_fake(monkeypatch, fake)
    result = runner.invoke(cli.app, ["chat", "--system", "Be terse.", "hi"])
    assert result.exit_code == 0, result.output
    assert fake.seen == [[SystemMessage(content="Be terse."), HumanMessage(content="hi")]]


def test_chat_json_output(monkeypatch: pytest.MonkeyPatch, configured: None) -> None:
    install_fake(monkeypatch, FakeListChatModel(responses=["json reply"]))
    result = runner.invoke(cli.app, ["chat", "--json", "hi"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"model": "fake-llama", "reply": "json reply"}


def test_chat_model_flag_overrides_setting(
    monkeypatch: pytest.MonkeyPatch, configured: None
) -> None:
    calls = install_fake(monkeypatch, FakeListChatModel(responses=["ok"]))
    result = runner.invoke(cli.app, ["chat", "--model", "other", "--json", "hi"])
    assert result.exit_code == 0, result.output
    assert calls[0][1] == "other"
    assert json.loads(result.stdout)["model"] == "other"


def test_chat_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGCHAINGOV_MODEL", "fake-llama")
    calls = install_fake(monkeypatch, FakeListChatModel(responses=["ok"]))
    result = runner.invoke(cli.app, ["chat", "hi"])
    assert result.exit_code == 1
    assert "LITELLM_API_KEY" in result.output
    assert calls == []


def test_chat_requires_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    calls = install_fake(monkeypatch, FakeListChatModel(responses=["ok"]))
    result = runner.invoke(cli.app, ["chat", "hi"])
    assert result.exit_code == 1
    assert "LANGCHAINGOV_MODEL" in result.output
    assert calls == []


def _request() -> httpx2.Request:
    return httpx2.Request("POST", "http://localhost:4000/v1/chat/completions")


def _response(status: int) -> httpx2.Response:
    return httpx2.Response(status, request=_request())


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (openai.APIConnectionError(request=_request()), "Could not reach LiteLLM"),
        (
            openai.AuthenticationError("nope", response=_response(401), body=None),
            "rejected the API key",
        ),
        (
            openai.NotFoundError("nope", response=_response(404), body=None),
            "does not know the model",
        ),
    ],
)
def test_chat_reports_client_errors(
    monkeypatch: pytest.MonkeyPatch, configured: None, error: Exception, expected: str
) -> None:
    install_fake(monkeypatch, RaisingChatModel(responses=["unused"], error=error))
    result = runner.invoke(cli.app, ["chat", "hi"])
    assert result.exit_code == 1
    assert expected in result.output


def test_message_text_flattens_content_blocks() -> None:
    from langchain_core.messages import AIMessage

    blocks: Sequence[str | dict[str, Any]] = [
        {"type": "text", "text": "Hello "},
        "world",
        {"type": "image", "url": "ignored"},
    ]
    assert message_text(AIMessage(content=list(blocks))) == "Hello world"


def test_models_lists_names(monkeypatch: pytest.MonkeyPatch, configured: None) -> None:
    monkeypatch.setattr(cli, "models_lister", lambda settings: ["b-model", "a-model"])
    result = runner.invoke(cli.app, ["models"])
    assert result.exit_code == 0, result.output
    assert result.stdout.split() == ["b-model", "a-model"]
    result = runner.invoke(cli.app, ["models", "--json"])
    assert json.loads(result.stdout) == {"models": ["b-model", "a-model"]}


def test_models_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[Settings] = []

    def lister(settings: Settings) -> list[str]:
        called.append(settings)
        return []

    monkeypatch.setattr(cli, "models_lister", lister)
    result = runner.invoke(cli.app, ["models"])
    assert result.exit_code == 1
    assert "LITELLM_API_KEY" in result.output
    assert called == []


def test_models_reports_connection_error(monkeypatch: pytest.MonkeyPatch, configured: None) -> None:
    def boom(settings: Settings) -> list[str]:
        raise openai.APIConnectionError(request=_request())

    monkeypatch.setattr(cli, "models_lister", boom)
    result = runner.invoke(cli.app, ["models"])
    assert result.exit_code == 1
    assert "Could not reach LiteLLM" in result.output
