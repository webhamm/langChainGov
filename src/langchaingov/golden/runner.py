"""Send golden-set payloads to the model with fixed parameters and record what came back.

The runner talks to the raw chat model, not ``GuardedChain``: it measures the model, and
it needs the reply's ``usage_metadata`` and ``finish_reason``. Cases run one after
another so latencies stay comparable between runs.
"""

import time
from collections.abc import Callable
from typing import Any

import openai
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from langchaingov.golden.generator import build_payload
from langchaingov.golden.models import GoldenSet, ModelProfile, Payload
from langchaingov.golden.scoring import score
from langchaingov.golden.store import CaseResult, RunWriter
from langchaingov.golden.tokens import TokenCounter
from langchaingov.llm import message_text

TRUNCATION_RATIO = 0.9
"""The model reporting fewer prompt tokens than this share of our estimate means the
server most likely cut the prompt (e.g. Ollama's num_ctx). Calibrated reports for the
local Llama run about 1% *above* the estimate, so 0.9 leaves a wide margin."""


class RunRefused(ValueError):
    """The run would break the local-first rule or the cloud token cap."""


def plan_run(
    golden: GoldenSet,
    profile: ModelProfile,
    levels: list[float],
    repeat: int,
    counter: TokenCounter,
    allow_cloud: bool,
    cloud_token_cap: int,
) -> list[Payload]:
    """Build every payload and check the run is allowed, before any request is sent."""
    if not profile.local and not allow_cloud:
        raise RunRefused(
            f"model {profile.name!r} is not marked local, and a context-filling run on a "
            "cloud model costs real money. Pass --allow-cloud to run it anyway."
        )
    payloads = [build_payload(golden, profile, level, counter) for level in levels]
    total = sum(p.est_tokens for p in payloads) * repeat
    if not profile.local and total > cloud_token_cap:
        raise RunRefused(
            f"this run would send about {total} prompt tokens to a cloud model, over the cap "
            f"of {cloud_token_cap}. Use fewer --level / --repeat, or raise --max-prompt-tokens."
        )
    return payloads


def run_case(golden: GoldenSet, payload: Payload, repeat: int, llm: BaseChatModel) -> CaseResult:
    """One request. A request the proxy rejects or that times out becomes the case's error;
    connection and auth errors propagate, because every later case would fail the same way."""
    messages = [SystemMessage(content=golden.system), HumanMessage(content=payload.prompt)]
    base: dict[str, Any] = {
        "case_id": payload.case_id,
        "level": payload.level,
        "repeat": repeat,
        "target_tokens": payload.target_tokens,
        "est_tokens": payload.est_tokens,
        "prompt_sha256": payload.sha256,
        "prompt_chars": payload.chars,
    }
    start = time.perf_counter()
    try:
        reply = llm.invoke(messages)
    except (openai.BadRequestError, openai.APITimeoutError) as exc:
        latency_ms = round((time.perf_counter() - start) * 1000)
        missed = score("", golden.needles)
        return CaseResult(
            **base,
            latency_ms=latency_ms,
            needles=missed.recalled,
            recall=missed.recall,
            error=f"{type(exc).__name__}: {exc}",
        )
    latency_ms = round((time.perf_counter() - start) * 1000)

    text = message_text(reply)
    usage = getattr(reply, "usage_metadata", None) or {}
    reported = usage.get("input_tokens")
    finish = reply.response_metadata.get("finish_reason")
    scores = score(text, golden.needles)
    return CaseResult(
        **base,
        reported_prompt_tokens=reported,
        completion_tokens=usage.get("output_tokens"),
        finish_reason=finish if isinstance(finish, str) else None,
        latency_ms=latency_ms,
        response=text,
        needles=scores.recalled,
        recall=scores.recall,
        suspected_truncation=reported is not None
        and reported < TRUNCATION_RATIO * payload.est_tokens,
    )


def execute_run(
    golden: GoldenSet,
    payloads: list[Payload],
    repeat: int,
    llm: BaseChatModel,
    writer: RunWriter,
    on_start: Callable[[Payload, int], None] | None = None,
    on_case: Callable[[CaseResult], None] | None = None,
) -> list[CaseResult]:
    """Every payload, ``repeat`` times, each result appended to the run file as it lands."""
    results: list[CaseResult] = []
    for payload in payloads:
        for index in range(1, repeat + 1):
            if on_start:
                on_start(payload, index)
            result = run_case(golden, payload, index, llm)
            writer.append(result)
            results.append(result)
            if on_case:
                on_case(result)
    return results
