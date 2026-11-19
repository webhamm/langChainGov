import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from langchaingov import cli
from langchaingov.golden.tokens import CharCounter, TokenizerUnavailable

runner = CliRunner()
MODEL = "llama3.2-3b-32k"


@pytest.fixture(autouse=True)
def offline_counter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "token_counter_factory", CharCounter)


def build_json(*args: str) -> dict[str, object]:
    result = runner.invoke(cli.app, ["golden", "build", "--json", *args])
    assert result.exit_code == 0, result.output
    data: dict[str, object] = json.loads(result.output)
    return data


def test_build_prints_the_ladder_without_a_proxy_or_key() -> None:
    result = runner.invoke(cli.app, ["golden", "build", "--model", MODEL])
    assert result.exit_code == 0, result.output
    for case in ("L025", "L050", "L075", "L090"):
        assert case in result.output
    assert "counted with chars/4" in result.output
    assert "(local)" in result.output


def test_model_falls_back_to_the_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGCHAINGOV_MODEL", MODEL)
    assert build_json()["model"] == MODEL


def test_json_is_stable_and_leaves_out_the_prompt() -> None:
    first = build_json("--model", MODEL)
    second = build_json("--model", MODEL)
    assert first == second
    payloads = first["payloads"]
    assert isinstance(payloads, list) and len(payloads) == 4
    assert "prompt" not in payloads[0]
    assert first["counter"] == "chars/4"
    assert first["context_tokens"] == 32768


def test_level_flag_picks_rungs() -> None:
    data = build_json("--model", MODEL, "--level", "0.5", "-l", "1.0")
    payloads = data["payloads"]
    assert isinstance(payloads, list)
    assert [p["case_id"] for p in payloads] == ["L050", "L100"]


def test_dump_writes_prompts_matching_their_hash(tmp_path: Path) -> None:
    out = tmp_path / "prompts"
    data = build_json("--model", MODEL, "--level", "0.25", "--dump", str(out))
    payloads = data["payloads"]
    assert isinstance(payloads, list)
    text = (out / "L025.txt").read_text(encoding="utf-8")
    assert hashlib.sha256(text.encode()).hexdigest() == payloads[0]["sha256"]


def test_unknown_model_needs_context() -> None:
    result = runner.invoke(cli.app, ["golden", "build", "--model", "mystery"])
    assert result.exit_code == 1
    assert "--context" in result.output


def test_unknown_model_with_context_builds_as_not_local() -> None:
    data = build_json("--model", "mystery", "--context", "8192")
    assert (data["context_tokens"], data["local"]) == (8192, False)


@pytest.mark.parametrize(
    "args",
    [
        ["--model", MODEL, "--level", "1.5"],
        ["--model", MODEL, "--set", "missing.yaml"],
        ["--model", "mystery", "--context", "500"],
    ],
)
def test_bad_input_exits_1(args: list[str]) -> None:
    result = runner.invoke(cli.app, ["golden", "build", *args])
    assert result.exit_code == 1
    assert "error:" in result.output


def test_tokenizer_unavailable_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    class Offline:
        name = "offline"

        def count(self, text: str) -> int:
            raise TokenizerUnavailable("tiktoken could not load 'o200k_base'")

    monkeypatch.setattr(cli, "token_counter_factory", Offline)
    result = runner.invoke(cli.app, ["golden", "build", "--model", MODEL])
    assert result.exit_code == 1
    assert "tiktoken could not load" in result.output
