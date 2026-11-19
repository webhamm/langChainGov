"""The golden runner against fake chat models. No network."""

from pathlib import Path

import httpx
import openai
import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from langchaingov.golden.loader import load_set
from langchaingov.golden.models import GoldenSet, ModelProfile, Payload
from langchaingov.golden.runner import RunRefused, execute_run, plan_run, run_case
from langchaingov.golden.store import CaseResult, RunWriter, read_run
from langchaingov.golden.tokens import CharCounter
from tests.fakes import UsageFakeChatModel
from tests.golden.test_scoring import PERFECT
from tests.golden.test_store import header

LOCAL = ModelProfile(name="local", context_tokens=8192, local=True)
CLOUD = ModelProfile(name="cloud", context_tokens=8192, local=False)
LEVELS = [0.25, 0.5]
REQUEST = httpx.Request("POST", "http://proxy.test/v1/chat/completions")


@pytest.fixture(scope="module")
def golden() -> GoldenSet:
    return load_set(None)


@pytest.fixture(scope="module")
def payloads(golden: GoldenSet) -> list[Payload]:
    return plan_run(golden, LOCAL, LEVELS, 1, CharCounter(), allow_cloud=False, cloud_token_cap=1)


def plan(
    golden: GoldenSet,
    profile: ModelProfile,
    *,
    repeat: int = 1,
    allow_cloud: bool = False,
    cloud_token_cap: int = 50_000,
) -> list[Payload]:
    return plan_run(golden, profile, LEVELS, repeat, CharCounter(), allow_cloud, cloud_token_cap)


def test_local_runs_ignore_the_cloud_cap(payloads: list[Payload]) -> None:
    assert [p.case_id for p in payloads] == ["L025", "L050"]


def test_cloud_needs_allow_cloud(golden: GoldenSet) -> None:
    with pytest.raises(RunRefused, match="--allow-cloud"):
        plan(golden, CLOUD)


def test_cloud_under_the_cap_is_allowed(golden: GoldenSet) -> None:
    assert len(plan(golden, CLOUD, allow_cloud=True)) == 2


def test_cloud_cap_counts_every_repeat(golden: GoldenSet, payloads: list[Payload]) -> None:
    once = sum(p.est_tokens for p in payloads)
    assert plan(golden, CLOUD, allow_cloud=True, cloud_token_cap=once)
    with pytest.raises(RunRefused, match="over the cap"):
        plan(golden, CLOUD, allow_cloud=True, cloud_token_cap=once, repeat=2)


def test_case_records_reply_usage_and_recall(golden: GoldenSet, payloads: list[Payload]) -> None:
    llm = UsageFakeChatModel(responses=[PERFECT])
    result = run_case(golden, payloads[0], 1, llm)
    assert result.recall == 1.0 and result.error is None
    assert result.response == PERFECT
    assert result.finish_reason == "stop"
    assert result.reported_prompt_tokens is not None
    assert result.reported_prompt_tokens >= payloads[0].est_tokens
    assert not result.suspected_truncation
    assert result.prompt_sha256 == payloads[0].sha256
    assert llm.seen[0] == [
        SystemMessage(content=golden.system),
        HumanMessage(content=payloads[0].prompt),
    ]


def test_short_reported_prompt_is_flagged_as_truncation(
    golden: GoldenSet, payloads: list[Payload]
) -> None:
    llm = UsageFakeChatModel(responses=[PERFECT], input_tokens=100)
    assert run_case(golden, payloads[1], 1, llm).suspected_truncation


@pytest.mark.parametrize(
    "error",
    [
        openai.BadRequestError(
            "context length exceeded", response=httpx.Response(400, request=REQUEST), body=None
        ),
        openai.APITimeoutError(request=REQUEST),
    ],
    ids=["bad-request", "timeout"],
)
def test_rejected_or_timed_out_request_becomes_the_case_error(
    golden: GoldenSet, payloads: list[Payload], error: Exception
) -> None:
    llm = UsageFakeChatModel(responses=[PERFECT], errors={0: error})
    result = run_case(golden, payloads[0], 1, llm)
    assert result.error is not None and type(error).__name__ in result.error
    assert result.recall == 0.0 and not any(result.needles.values())


def test_connection_errors_propagate(golden: GoldenSet, payloads: list[Payload]) -> None:
    llm = UsageFakeChatModel(
        responses=[PERFECT], errors={0: openai.APIConnectionError(request=REQUEST)}
    )
    with pytest.raises(openai.APIConnectionError):
        run_case(golden, payloads[0], 1, llm)


def test_execute_run_writes_every_case_and_continues_past_errors(
    golden: GoldenSet, payloads: list[Payload], tmp_path: Path
) -> None:
    bad = openai.BadRequestError("nope", response=httpx.Response(400, request=REQUEST), body=None)
    llm = UsageFakeChatModel(responses=[PERFECT], errors={1: bad})
    started: list[tuple[str, int]] = []
    finished: list[CaseResult] = []
    path = tmp_path / "run.jsonl"
    with RunWriter(path, header()) as writer:
        results = execute_run(
            golden,
            payloads,
            2,
            llm,
            writer,
            on_start=lambda p, i: started.append((p.case_id, i)),
            on_case=finished.append,
        )
    assert started == [("L025", 1), ("L025", 2), ("L050", 1), ("L050", 2)]
    assert [r.error is not None for r in results] == [False, True, False, False]
    assert finished == results
    assert read_run(path)[1] == results
