import hashlib
import json
from pathlib import Path

import httpx
import openai
import pytest
from langchain_core.language_models import BaseChatModel
from typer.testing import CliRunner

from langchaingov import cli
from langchaingov.golden.store import RequestParams, read_run
from langchaingov.golden.tokens import CharCounter, TokenizerUnavailable
from langchaingov.settings import Settings
from tests.fakes import UsageFakeChatModel
from tests.golden.test_scoring import PERFECT

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


REQUEST = httpx.Request("POST", "http://proxy.test/v1/chat/completions")


class FakeFactory:
    """Stands in for ``cli.golden_model_factory`` and remembers what it was asked for."""

    def __init__(self, llm: UsageFakeChatModel) -> None:
        self.llm = llm
        self.params: RequestParams | None = None

    def __call__(self, settings: Settings, model: str, params: RequestParams) -> BaseChatModel:
        self.params = params
        return self.llm


@pytest.fixture
def fake_model(monkeypatch: pytest.MonkeyPatch) -> FakeFactory:
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    factory = FakeFactory(UsageFakeChatModel(responses=[PERFECT]))
    monkeypatch.setattr(cli, "golden_model_factory", factory)
    return factory


def run_files(root: Path = Path("runs/golden")) -> list[Path]:
    return sorted(root.glob("*.jsonl")) if root.exists() else []


def test_run_writes_a_run_file_with_pinned_params(fake_model: FakeFactory) -> None:
    result = runner.invoke(cli.app, ["golden", "run", "--model", MODEL])
    assert result.exit_code == 0, result.output
    [path] = run_files()
    header, cases = read_run(path)
    assert [c.case_id for c in cases] == ["L025", "L050", "L075", "L090"]
    assert all(c.recall == 1.0 for c in cases)
    assert header.model == MODEL and header.profile.local
    assert header.params == fake_model.params
    assert fake_model.params is not None
    assert (fake_model.params.max_tokens, fake_model.params.timeout_s) == (1024, 600)
    assert fake_model.params.max_retries == 0
    assert fake_model.params.seed_sent == fake_model.params.seed_requested == 20261119
    assert header.run_id in result.output


def test_run_json_summary(fake_model: FakeFactory) -> None:
    result = runner.invoke(
        cli.app, ["golden", "run", "--model", MODEL, "-l", "0.25", "--repeat", "2", "--json"]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["errored"] == 0
    assert [(c["case_id"], c["repeat"]) for c in data["cases"]] == [("L025", 1), ("L025", 2)]
    assert "response" not in data["cases"][0]
    assert Path(data["path"]).exists()


def test_runs_dir_setting(fake_model: FakeFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGCHAINGOV_RUNS_DIR", "elsewhere")
    assert runner.invoke(cli.app, ["golden", "run", "--model", MODEL, "-l", "0.25"]).exit_code == 0
    assert len(run_files(Path("elsewhere"))) == 1


def test_cloud_model_is_refused_before_any_request(fake_model: FakeFactory) -> None:
    result = runner.invoke(cli.app, ["golden", "run", "--model", "mystery", "--context", "8192"])
    assert result.exit_code == 1
    assert "--allow-cloud" in result.output
    assert fake_model.llm.calls == 0 and run_files() == []


def test_cloud_cap_is_enforced(fake_model: FakeFactory) -> None:
    args = ["golden", "run", "--model", "mystery", "--context", "8192", "--allow-cloud"]
    result = runner.invoke(cli.app, [*args, "--max-prompt-tokens", "1000"])
    assert result.exit_code == 1
    assert "over the cap" in result.output
    assert fake_model.llm.calls == 0


def test_allowed_cloud_run_sends_no_seed_without_profile_support(
    fake_model: FakeFactory,
) -> None:
    args = ["golden", "run", "--model", "mystery", "--context", "8192", "--allow-cloud"]
    assert runner.invoke(cli.app, [*args, "-l", "0.25"]).exit_code == 0
    assert fake_model.params is not None and fake_model.params.seed_sent is None


def test_case_errors_exit_4_and_keep_going(fake_model: FakeFactory) -> None:
    bad = openai.BadRequestError(
        "too long", response=httpx.Response(400, request=REQUEST), body=None
    )
    fake_model.llm.errors = {0: bad}
    result = runner.invoke(cli.app, ["golden", "run", "--model", MODEL, "-l", "0.25", "-l", "0.5"])
    assert result.exit_code == 4
    [path] = run_files()
    assert [c.error is not None for c in read_run(path)[1]] == [True, False]


def test_connection_error_exits_1_and_keeps_the_header(fake_model: FakeFactory) -> None:
    fake_model.llm.errors = {0: openai.APIConnectionError(request=REQUEST)}
    result = runner.invoke(cli.app, ["golden", "run", "--model", MODEL, "-l", "0.25"])
    assert result.exit_code == 1
    assert "Could not reach LiteLLM" in result.output
    [path] = run_files()
    assert read_run(path)[1] == []


def test_run_needs_key_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    result = runner.invoke(cli.app, ["golden", "run", "--model", MODEL])
    assert result.exit_code == 1 and "LITELLM_API_KEY" in result.output
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    result = runner.invoke(cli.app, ["golden", "run"])
    assert result.exit_code == 1 and "No model configured" in result.output
