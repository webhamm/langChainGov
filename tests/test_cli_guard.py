import json

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from typer.testing import CliRunner

from langchaingov import cli
from langchaingov.guards import registry
from langchaingov.settings import Settings
from tests.fakes import StubGuard

runner = CliRunner()


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    monkeypatch.setenv("LANGCHAINGOV_MODEL", "fake-llama")


def install_fake(monkeypatch: pytest.MonkeyPatch, reply: str = "the reply") -> None:
    def factory(settings: Settings, model: str | None) -> BaseChatModel:
        return FakeListChatModel(responses=[reply])

    monkeypatch.setattr(cli, "model_factory", factory)


def test_guard_list_shows_builtins() -> None:
    result = runner.invoke(cli.app, ["guard", "list"])
    assert result.exit_code == 0, result.output
    assert "keyword-blocklist" in result.stdout

    result = runner.invoke(cli.app, ["guard", "list", "--json"])
    names = [row["name"] for row in json.loads(result.stdout)]
    assert "keyword-blocklist" in names


def test_guard_run_allows(monkeypatch: pytest.MonkeyPatch, configured: None) -> None:
    install_fake(monkeypatch)
    result = runner.invoke(cli.app, ["guard", "run", "--guard", "keyword-blocklist", "hello"])
    assert result.exit_code == 0, result.output
    assert "the reply" in result.stdout
    assert "allow" in result.stdout


def test_guard_run_blocks_with_exit_2(monkeypatch: pytest.MonkeyPatch, configured: None) -> None:
    install_fake(monkeypatch)
    result = runner.invoke(
        cli.app, ["guard", "run", "--guard", "keyword-blocklist", "how to mine blorptium"]
    )
    assert result.exit_code == 2, result.output
    assert "Blocked: keyword-blocklist (input): contains blocked word 'blorptium'" in result.stdout
    assert "the reply" not in result.stdout


def test_guard_run_json(monkeypatch: pytest.MonkeyPatch, configured: None) -> None:
    install_fake(monkeypatch)
    result = runner.invoke(
        cli.app, ["guard", "run", "--guard", "keyword-blocklist", "--json", "hello"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["model"] == "fake-llama"
    assert payload["blocked"] is False
    assert payload["reply"] == "the reply"
    assert [v["stage"] for v in payload["verdicts"]] == ["input", "output"]


def test_guard_run_blocks_output(monkeypatch: pytest.MonkeyPatch, configured: None) -> None:
    install_fake(monkeypatch, reply="the zanthar protocol says hi")
    result = runner.invoke(
        cli.app, ["guard", "run", "--guard", "keyword-blocklist", "--json", "hello"]
    )
    assert result.exit_code == 2, result.output
    payload = json.loads(result.stdout)
    assert payload["blocked"] is True
    assert payload["reply"] is None
    assert payload["block_reason"].startswith("keyword-blocklist (output)")


def test_guard_run_applies_guards_in_order(
    monkeypatch: pytest.MonkeyPatch, configured: None, clean_registry: None
) -> None:
    install_fake(monkeypatch)
    registry.register("one", "first", lambda s, m: StubGuard("one", on_input=("modify", "up")))
    registry.register("two", "second", lambda s, m: StubGuard("two"))
    result = runner.invoke(cli.app, ["guard", "run", "-g", "one", "-g", "two", "--json", "hello"])
    assert result.exit_code == 0, result.output
    verdicts = json.loads(result.stdout)["verdicts"]
    assert [(v["guard"], v["stage"], v["action"]) for v in verdicts] == [
        ("one", "input", "modify"),
        ("two", "input", "allow"),
        ("one", "output", "allow"),
        ("two", "output", "allow"),
    ]
    assert verdicts[1]["text"] == "HELLO"


def test_guard_run_unknown_guard(monkeypatch: pytest.MonkeyPatch, configured: None) -> None:
    install_fake(monkeypatch)
    result = runner.invoke(cli.app, ["guard", "run", "--guard", "nope", "hello"])
    assert result.exit_code == 1
    assert "unknown guard 'nope'" in result.output


def test_guard_run_requires_config(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake(monkeypatch)
    result = runner.invoke(cli.app, ["guard", "run", "--guard", "keyword-blocklist", "hello"])
    assert result.exit_code == 1
    assert "LITELLM_API_KEY" in result.output
