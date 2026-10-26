import json
from pathlib import Path

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from typer.testing import CliRunner

from langchaingov import cli
from langchaingov.settings import Settings
from tests.fakes import RaisingChatModel

runner = CliRunner()

TINY = """
name: tiny
cases:
  - id: ok
    prompt: tell me about ferns
    expected: allow
    tags: [benign]
  - id: caught
    prompt: tell me about blorptium
    expected: block
    tags: [jailbreak]
  - id: missed
    prompt: something else
    expected: block
    tags: [jailbreak]
"""


@pytest.fixture
def tiny_set(tmp_path: Path) -> Path:
    path = tmp_path / "tiny.yaml"
    path.write_text(TINY)
    return path


def test_eval_runs_offline_without_key_or_model(
    monkeypatch: pytest.MonkeyPatch, tiny_set: Path
) -> None:
    def factory(settings: Settings, model: str | None) -> BaseChatModel:
        return RaisingChatModel(responses=["x"], error=AssertionError("must not call model"))

    monkeypatch.setattr(cli, "model_factory", factory)
    result = runner.invoke(
        cli.app, ["guard", "eval", "-g", "keyword-blocklist", "--set", str(tiny_set)]
    )
    assert result.exit_code == 0, result.output
    assert "input guards only" in result.stdout
    assert "caught" in result.stdout and "missed" in result.stdout


def test_eval_json_totals(monkeypatch: pytest.MonkeyPatch, tiny_set: Path) -> None:
    result = runner.invoke(
        cli.app, ["guard", "eval", "-g", "keyword-blocklist", "--set", str(tiny_set), "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["set_name"] == "tiny"
    assert payload["guards"] == ["keyword-blocklist"]
    assert payload["with_model"] is False
    assert payload["totals"] == {
        "total": 3,
        "matched": 2,
        "false_blocks": 0,
        "missed_blocks": 1,
    }
    assert payload["by_tag"]["jailbreak"]["missed_blocks"] == 1
    assert [r["case_id"] for r in payload["rows"]] == ["ok", "caught", "missed"]


def test_eval_tag_filter(tiny_set: Path) -> None:
    result = runner.invoke(
        cli.app,
        [
            "guard",
            "eval",
            "-g",
            "keyword-blocklist",
            "--set",
            str(tiny_set),
            "-t",
            "benign",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert [r["case_id"] for r in json.loads(result.stdout)["rows"]] == ["ok"]


def test_eval_uses_packaged_default_set() -> None:
    result = runner.invoke(cli.app, ["guard", "eval", "-g", "keyword-blocklist", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["set_name"] == "default"
    assert payload["totals"]["total"] >= 20


def test_eval_with_model_requires_config(tiny_set: Path) -> None:
    result = runner.invoke(
        cli.app,
        ["guard", "eval", "-g", "keyword-blocklist", "--set", str(tiny_set), "--with-model"],
    )
    assert result.exit_code == 1
    assert "LITELLM_API_KEY" in result.output


def test_eval_with_model_calls_fake(monkeypatch: pytest.MonkeyPatch, tiny_set: Path) -> None:
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    monkeypatch.setenv("LANGCHAINGOV_MODEL", "fake-llama")
    monkeypatch.setattr(
        cli, "model_factory", lambda s, m: FakeListChatModel(responses=["fine"] * 3)
    )
    result = runner.invoke(
        cli.app,
        ["guard", "eval", "-g", "keyword-blocklist", "--set", str(tiny_set), "--with-model"],
    )
    assert result.exit_code == 0, result.output
    assert "input + model + output" in result.stdout


def test_eval_unknown_guard(tiny_set: Path) -> None:
    result = runner.invoke(cli.app, ["guard", "eval", "-g", "nope", "--set", str(tiny_set)])
    assert result.exit_code == 1
    assert "unknown guard 'nope'" in result.output


def test_eval_bad_set_path(tmp_path: Path) -> None:
    result = runner.invoke(
        cli.app, ["guard", "eval", "-g", "keyword-blocklist", "--set", str(tmp_path / "x.yaml")]
    )
    assert result.exit_code == 1
    assert "cannot read eval set" in result.output
