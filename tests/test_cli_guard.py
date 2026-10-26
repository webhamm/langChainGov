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
    for name in [
        "keyword-blocklist",
        "pii-regex",
        "topic-allowlist",
        "llm-judge",
        "lc-pii",
        "lc-hitl",
        "lc-custom-hooks",
        "gr-pii",
        "gr-toxic",
        "gr-topic",
    ]:
        assert name in result.stdout

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


def test_guard_run_redaction_reaches_model(
    monkeypatch: pytest.MonkeyPatch, configured: None
) -> None:
    from tests.fakes import RecordingChatModel

    fake = RecordingChatModel(responses=["noted"])
    monkeypatch.setattr(cli, "model_factory", lambda s, m: fake)
    result = runner.invoke(
        cli.app, ["guard", "run", "-g", "pii-regex", "--json", "email me at jane.doe@example.com"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["blocked"] is False
    assert payload["verdicts"][0]["action"] == "modify"
    assert str(fake.seen[0][-1].content) == "email me at [EMAIL]"


def test_guard_run_proxy_error_is_reported_not_blocked(
    monkeypatch: pytest.MonkeyPatch, configured: None
) -> None:
    import httpx
    import openai

    from tests.fakes import RaisingChatModel

    error = openai.APIConnectionError(
        request=httpx.Request("POST", "http://localhost:4000/v1/chat/completions")
    )
    monkeypatch.setattr(
        cli, "model_factory", lambda s, m: RaisingChatModel(responses=["x"], error=error)
    )
    result = runner.invoke(cli.app, ["guard", "run", "-g", "llm-judge", "hello"])
    assert result.exit_code == 1
    assert "Could not reach LiteLLM" in result.output


@pytest.mark.parametrize(("answer", "code"), [("y\n", 0), ("n\n", 2)])
def test_guard_run_hitl_asks_in_terminal(
    monkeypatch: pytest.MonkeyPatch, configured: None, answer: str, code: int
) -> None:
    from langchaingov.guards.middleware import hitl

    install_fake(monkeypatch)
    result = runner.invoke(cli.app, ["guard", "run", "-g", "lc-hitl", "hello"], input=answer)
    assert result.exit_code == code, result.output
    assert "review this input" in result.output
    assert hitl.default_policy is None  # reset after the run


def test_guard_eval_hitl_auto_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    result = runner.invoke(cli.app, ["guard", "eval", "-g", "lc-hitl", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert all(r["actual"] == "block" for r in payload["rows"])
    assert payload["totals"]["false_blocks"] == payload["by_tag"]["benign"]["total"]


def test_guard_run_missing_extra_hint(monkeypatch: pytest.MonkeyPatch, configured: None) -> None:
    from langchaingov.guards import guardrails_ai

    install_fake(monkeypatch)
    monkeypatch.setattr(guardrails_ai, "is_installed", lambda: False)
    result = runner.invoke(cli.app, ["guard", "run", "-g", "gr-pii", "hello"])
    assert result.exit_code == 1
    assert "guard 'gr-pii' needs the 'guardrails-ai' extra: uv sync --extra guardrails-ai" in (
        result.output
    )
